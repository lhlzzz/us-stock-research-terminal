"""Market regime detection for US stock pipeline.

Analogous to xiaogu's market_regime_profile() but adapted for US markets:
- breadth: % of universe above 20d MA
- momentum: SPY/QQQ 20d return
- volatility: ATR-based or VIX proxy
- advance_ratio: % of stocks with positive daily return

Four regimes: risk_on, active, balanced, risk_off
Each regime defines: scoring weights, exhaustion threshold, position cap, min score gate.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class MarketRegime:
    name: str
    breadth: float
    momentum: float
    volatility: float
    advance_ratio: float


@dataclass
class RegimeThresholds:
    scoring_weights: dict[str, float]
    exhaustion_threshold: float
    exhaustion_adjustment: float
    position_cap_pct: float
    min_market_score_gate: float
    kelly_fraction_cap: float
    stop_loss_multiplier: float
    take_profit_multiplier: float
    risk_per_trade: float
    max_single_position_pct: float
    max_total_exposure_pct: float
    max_consecutive_losses: int
    daily_max_loss_r: float
    default_stop_loss_pct: float
    accel_hard_block_threshold: float
    blowoff_volume_threshold: float
    blowoff_closing_threshold: float
    blowoff_accel_threshold: float
    description: str


REGIME_THRESHOLDS: dict[str, RegimeThresholds] = {
    "risk_on": RegimeThresholds(
        scoring_weights={
        "prior_20d_momentum": 0.10,
        "five_day_acceleration": -0.10,
        "relative_strength_vs_equal_weight": 0.45,
        "volume_weighted_momentum": 0.30,
        "closing_strength_5d": 0.0,
        "volume_confirmation_ratio": 0.0,
    },
        exhaustion_threshold=-0.22,
        exhaustion_adjustment=-0.03,
        position_cap_pct=0.15,
        min_market_score_gate=0.0,
        kelly_fraction_cap=1.0,
        stop_loss_multiplier=1.2,
        take_profit_multiplier=0.8,
        risk_per_trade=0.03,
        max_single_position_pct=0.15,
        max_total_exposure_pct=0.60,
        max_consecutive_losses=3,
        daily_max_loss_r=4.0,
        default_stop_loss_pct=0.018,
        accel_hard_block_threshold=-0.18,
        blowoff_volume_threshold=0.6,
        blowoff_closing_threshold=0.35,
        blowoff_accel_threshold=-0.12,
        description="Lenient accel gate, let momentum run",
    ),
    "active": RegimeThresholds(
        scoring_weights={
        "prior_20d_momentum": 0.10,
        "five_day_acceleration": -0.10,
        "relative_strength_vs_equal_weight": 0.45,
        "volume_weighted_momentum": 0.30,
        "closing_strength_5d": 0.0,
        "volume_confirmation_ratio": 0.0,
    },
        exhaustion_threshold=-0.22,
        exhaustion_adjustment=-0.04,
        position_cap_pct=0.12,
        min_market_score_gate=0.0,
        kelly_fraction_cap=0.8,
        stop_loss_multiplier=1.0,
        take_profit_multiplier=1.0,
        risk_per_trade=0.02,
        max_single_position_pct=0.10,
        max_total_exposure_pct=0.50,
        max_consecutive_losses=2,
        daily_max_loss_r=3.0,
        default_stop_loss_pct=0.018,
        accel_hard_block_threshold=-0.15,
        blowoff_volume_threshold=0.55,
        blowoff_closing_threshold=0.38,
        blowoff_accel_threshold=-0.10,
        description="Moderate accel gate, balanced risk",
    ),
    "balanced": RegimeThresholds(
        scoring_weights={
        "prior_20d_momentum": 0.10,
        "five_day_acceleration": -0.10,
        "relative_strength_vs_equal_weight": 0.45,
        "volume_weighted_momentum": 0.30,
        "closing_strength_5d": 0.0,
        "volume_confirmation_ratio": 0.0,
    },
        exhaustion_threshold=-0.18,
        exhaustion_adjustment=-0.06,
        position_cap_pct=0.10,
        min_market_score_gate=0.55,
        kelly_fraction_cap=0.6,
        stop_loss_multiplier=0.8,
        take_profit_multiplier=1.2,
        risk_per_trade=0.015,
        max_single_position_pct=0.08,
        max_total_exposure_pct=0.40,
        max_consecutive_losses=2,
        daily_max_loss_r=2.5,
        default_stop_loss_pct=0.012,
        accel_hard_block_threshold=-0.12,
        blowoff_volume_threshold=0.5,
        blowoff_closing_threshold=0.4,
        blowoff_accel_threshold=-0.10,
        description="Standard accel gate, tighter risk",
    ),
    "risk_off": RegimeThresholds(
        scoring_weights={
        "prior_20d_momentum": 0.10,
        "five_day_acceleration": -0.10,
        "relative_strength_vs_equal_weight": 0.45,
        "volume_weighted_momentum": 0.30,
        "closing_strength_5d": 0.0,
        "volume_confirmation_ratio": 0.0,
    },
        exhaustion_threshold=-0.12,
        exhaustion_adjustment=-0.10,
        position_cap_pct=0.05,
        min_market_score_gate=0.70,
        kelly_fraction_cap=0.3,
        stop_loss_multiplier=0.6,
        take_profit_multiplier=1.5,
        risk_per_trade=0.01,
        max_single_position_pct=0.05,
        max_total_exposure_pct=0.25,
        max_consecutive_losses=1,
        daily_max_loss_r=1.5,
        default_stop_loss_pct=0.008,
        accel_hard_block_threshold=-0.08,
        blowoff_volume_threshold=0.45,
        blowoff_closing_threshold=0.42,
        blowoff_accel_threshold=-0.08,
        description="Strictest accel gate, protect capital",
    ),
}


def classify_market_regime(
    close_panel: pd.DataFrame,
    universe_symbols: list[str],
    lookback: int = 20,
) -> MarketRegime:
    """Classify market regime from universe price data.

    Uses:
    - breadth: % of stocks with positive 20d return
    - momentum: median 20d return across universe
    - volatility: median ATR/price ratio
    - advance_ratio: % of stocks with positive 1d return
    """
    if close_panel.empty or len(close_panel) < lookback + 1:
        return MarketRegime(name="balanced", breadth=50.0, momentum=0.0, volatility=0.02, advance_ratio=50.0)

    recent = close_panel.tail(lookback + 1)
    available = [s for s in universe_symbols if s in recent.columns]
    if len(available) < 10:
        return MarketRegime(name="balanced", breadth=50.0, momentum=0.0, volatility=0.02, advance_ratio=50.0)

    returns_20d = (recent.iloc[-1][available] / recent.iloc[0][available] - 1.0).dropna()
    breadth = float((returns_20d > 0).mean() * 100) if len(returns_20d) > 0 else 50.0

    momentum = float(returns_20d.median()) if len(returns_20d) > 0 else 0.0

    daily_returns = recent.pct_change().dropna()
    atr_proxy = daily_returns[available].abs().median()
    volatility = float(atr_proxy.mean()) if len(atr_proxy) > 0 else 0.02

    last_day_return = (recent.iloc[-1][available] / recent.iloc[-2][available] - 1.0).dropna()
    advance_ratio = float((last_day_return > 0).mean() * 100) if len(last_day_return) > 0 else 50.0

    if breadth >= 65.0 and momentum >= 0.03:
        name = "risk_on"
    elif breadth >= 45.0 and momentum >= 0.0:
        name = "active"
    elif breadth >= 30.0:
        name = "balanced"
    else:
        name = "risk_off"

    return MarketRegime(
        name=name,
        breadth=round(breadth, 1),
        momentum=round(momentum, 4),
        volatility=round(volatility, 4),
        advance_ratio=round(advance_ratio, 1),
    )


def get_regime_thresholds(regime_name: str) -> RegimeThresholds:
    return REGIME_THRESHOLDS.get(regime_name, REGIME_THRESHOLDS["active"])


def format_regime_summary(regime: MarketRegime, thresholds: RegimeThresholds) -> str:
    lines = [
        f"## Market Regime: {regime.name.upper()}",
        f"- breadth: {regime.breadth:.1f}% (stocks with positive 20d return)",
        f"- momentum: {regime.momentum:+.2%} (median 20d return)",
        f"- volatility: {regime.volatility:.4f} (median daily |return|)",
        f"- advance_ratio: {regime.advance_ratio:.1f}% (1d advancers)",
        f"- description: {thresholds.description}",
        f"- scoring_weights: {thresholds.scoring_weights}",
        f"- exhaustion_threshold: {thresholds.exhaustion_threshold}",
        f"- position_cap: {thresholds.position_cap_pct:.0%}",
        f"- min_market_score_gate: {thresholds.min_market_score_gate}",
        f"- kelly_fraction_cap: {thresholds.kelly_fraction_cap:.0%}",
        f"- stop_loss_multiplier: {thresholds.stop_loss_multiplier:.1f}x",
        f"- take_profit_multiplier: {thresholds.take_profit_multiplier:.1f}x",
        f"- risk_per_trade: {thresholds.risk_per_trade:.1%}",
        f"- max_single_position: {thresholds.max_single_position_pct:.0%}",
        f"- max_total_exposure: {thresholds.max_total_exposure_pct:.0%}",
        f"- max_consecutive_losses: {thresholds.max_consecutive_losses}",
        f"- daily_max_loss_r: {thresholds.daily_max_loss_r:.1f}R",
        f"- default_stop_loss: {thresholds.default_stop_loss_pct:.1%}",
    ]
    return "\n".join(lines)
