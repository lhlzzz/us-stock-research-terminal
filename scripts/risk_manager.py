#!/usr/bin/env python3
"""Risk management module for xiaomei profit-ticket pipeline.

Integrates best practices from:
- Reddit r/Daytrading: fixed-fractional sizing, trailing stops, daily loss limits
- Reddit r/algotrading: algo-based risk controls
- YouTube: Claude AI signal → Telegram alert pipeline
- GitHub: position sizing calculators, guardian agent pattern
- 东方财富: Kelly Criterion, avoid small-cap quant-dominated stocks
- Polymarket: probability-weighted position sizing

Boundary: research-only. No broker/order/ledger/live-trade. No BUY/SELL.
Outputs risk parameters and position sizing for paper review only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ─── Constants (derived from cross-platform research) ─────────────────────────

# Reddit consensus: risk 1-2% per trade
DEFAULT_RISK_PER_TRADE = 0.02

# Reddit + YouTube: trailing stop activates at 1.5R profit
TRAILING_STOP_ACTIVATION_R = 1.5

# GitHub repos: trail at 50% of max unrealized profit
TRAILING_STOP_TRAIL_PCT = 0.50

# Reddit prop firm standard: daily max loss = 3R
DAILY_MAX_LOSS_R = 3.0

# Reddit: cooldown after 2 consecutive losses
MAX_CONSECUTIVE_LOSSES = 2

# 东方财富: Kelly Criterion half-Kelly for safety
KELLY_FRACTION = 0.5

# Reddit: never add to losers
ALLOW_AVERAGING_DOWN = False

# Maximum single position as % of portfolio
MAX_SINGLE_POSITION_PCT = 0.10

# Maximum total exposure
MAX_TOTAL_EXPOSURE_PCT = 0.50


@dataclass
class RiskParameters:
    """Per-trade risk parameters."""
    entry_price: float
    stop_loss_pct: float
    take_profit_pct: float
    position_size_pct: float
    risk_per_share: float
    reward_per_share: float
    risk_reward_ratio: float
    kelly_fraction: float
    half_kelly: float
    trailing_stop_activation: float
    trailing_stop_pct: float
    daily_max_loss_r: float
    max_consecutive_losses: int
    cooldown_required: bool


@dataclass
class RiskState:
    """Portfolio-level risk state for daily management."""
    daily_pnl: float = 0.0
    daily_loss_limit: float = 0.0
    consecutive_losses: int = 0
    total_exposure_pct: float = 0.0
    open_positions: int = 0
    trades_today: int = 0
    is_cooldown: bool = False
    is_daily_limit_hit: bool = False


@dataclass
class TradeRiskAssessment:
    """Assessment of a single trade's risk."""
    symbol: str
    risk_parameters: RiskParameters
    risk_state: RiskState
    allowed: bool
    block_reason: str
    suggested_position_size: float
    suggested_stop_loss: float
    suggested_take_profit: float
    risk_score: float
    confidence: float


def calculate_position_size(
    account_balance: float,
    entry_price: float,
    stop_loss_pct: float,
    risk_per_trade: float = DEFAULT_RISK_PER_TRADE,
) -> float:
    """Fixed-fractional position sizing (Reddit #1 consensus).

    Returns the number of shares to buy.
    """
    if entry_price <= 0 or stop_loss_pct <= 0:
        return 0.0
    risk_amount = account_balance * risk_per_trade
    risk_per_share = entry_price * stop_loss_pct
    if risk_per_share <= 0:
        return 0.0
    return risk_amount / risk_per_share


def calculate_kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = KELLY_FRACTION,
) -> float:
    """Kelly Criterion with half-Kelly safety (东方财富 + GitHub best practice).

    Returns the fraction of bankroll to risk.
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    kelly = (win_rate * b - (1 - win_rate)) / b
    kelly = max(0.0, kelly)
    return kelly * fraction


def calculate_stop_loss(
    entry_price: float,
    atr: float | None = None,
    fixed_pct: float = 0.02,
) -> float:
    """Stop loss calculation. Uses ATR if available, otherwise fixed percentage."""
    if atr is not None and atr > 0:
        return entry_price - 2.0 * atr
    return entry_price * (1 - fixed_pct)


def calculate_take_profit(
    entry_price: float,
    stop_loss: float,
    risk_reward_ratio: float = 2.0,
) -> float:
    """Take profit based on risk-reward ratio (Reddit consensus: 2R minimum)."""
    risk = entry_price - stop_loss
    return entry_price + risk * risk_reward_ratio


def calculate_trailing_stop(
    entry_price: float,
    current_price: float,
    max_price: float,
    activation_r: float = TRAILING_STOP_ACTIVATION_R,
    trail_pct: float = TRAILING_STOP_TRAIL_PCT,
) -> float | None:
    """Trailing stop (Reddit advanced technique + GitHub DQN repos).

    Returns None if trailing stop hasn't activated yet.
    Trailing stop = max_price - trail_pct * (max_price - entry_price).
    Never below entry price.
    """
    risk = entry_price * 0.02  # assume 2% risk
    if risk <= 0:
        return None
    profit_in_r = (current_price - entry_price) / risk
    if profit_in_r < activation_r:
        return None
    profit_range = max_price - entry_price
    trailing = max_price - trail_pct * profit_range
    return max(trailing, entry_price)


def assess_trade_risk(
    symbol: str,
    entry_price: float,
    current_price: float,
    account_balance: float,
    win_rate: float = 0.5,
    avg_win_pct: float = 0.04,
    avg_loss_pct: float = 0.02,
    atr: float | None = None,
    risk_state: RiskState | None = None,
    risk_per_trade: float = DEFAULT_RISK_PER_TRADE,
    default_stop_loss_pct: float | None = None,
    max_single_position_pct: float = MAX_SINGLE_POSITION_PCT,
    max_total_exposure_pct: float = MAX_TOTAL_EXPOSURE_PCT,
    max_consecutive_losses: int = MAX_CONSECUTIVE_LOSSES,
    daily_max_loss_r: float = DAILY_MAX_LOSS_R,
) -> TradeRiskAssessment:
    """Full risk assessment for a single trade.

    Combines:
    - Fixed-fractional position sizing (Reddit)
    - Kelly Criterion (东方财富)
    - Daily loss limit (Reddit prop firm)
    - Consecutive loss cooldown (Reddit)
    - Stop loss / take profit / trailing stop
    """
    if risk_state is None:
        risk_state = RiskState()

    stop_loss_pct = default_stop_loss_pct if default_stop_loss_pct is not None else avg_loss_pct
    stop_loss = calculate_stop_loss(entry_price, atr, stop_loss_pct)
    take_profit = calculate_take_profit(entry_price, stop_loss, 2.0)

    position_size_pct = risk_per_trade
    kelly = calculate_kelly_fraction(win_rate, avg_win_pct, avg_loss_pct)
    half_kelly = kelly

    if kelly <= 0:
        position_size_pct = 0.0
    elif kelly < 0.05:
        position_size_pct = min(risk_per_trade, kelly * 2)
    elif kelly < 0.10:
        position_size_pct = min(risk_per_trade, kelly * 1.5)
    else:
        position_size_pct = risk_per_trade

    risk_per_share = entry_price - stop_loss
    reward_per_share = take_profit - entry_price
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0

    shares = calculate_position_size(
        account_balance, entry_price, stop_loss_pct, position_size_pct
    )
    position_value = shares * entry_price
    position_pct = position_value / account_balance if account_balance > 0 else 0.0

    allowed = True
    block_reason = ""

    if risk_state.is_cooldown or risk_state.consecutive_losses >= max_consecutive_losses:
        allowed = False
        block_reason = f"cooldown_active: {risk_state.consecutive_losses} consecutive losses"
    elif risk_state.is_daily_limit_hit:
        allowed = False
        block_reason = f"daily_loss_limit_hit: daily_pnl={risk_state.daily_pnl:.2f}"
    elif position_pct > max_single_position_pct:
        position_pct = max_single_position_pct
        shares = (account_balance * max_single_position_pct) / entry_price if entry_price > 0 else 0.0
        position_value = shares * entry_price
        position_pct = position_value / account_balance if account_balance > 0 else 0.0
    elif risk_state.total_exposure_pct + position_pct > max_total_exposure_pct:
        allowed = False
        block_reason = f"max_exposure_exceeded: current={risk_state.total_exposure_pct:.1%} + new={position_pct:.1%}"

    trailing_activation = entry_price + risk_per_share * TRAILING_STOP_ACTIVATION_R

    risk_score = 0.0
    if rr_ratio < 1.5:
        risk_score += 0.3
    if stop_loss_pct > 0.03:
        risk_score += 0.2
    if kelly < 0.01:
        risk_score += 0.2
    if risk_state.consecutive_losses >= 1:
        risk_score += 0.1 * risk_state.consecutive_losses

    confidence = min(1.0, max(0.0, 1.0 - risk_score))

    return TradeRiskAssessment(
        symbol=symbol,
        risk_parameters=RiskParameters(
            entry_price=entry_price,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=(take_profit / entry_price - 1) if entry_price > 0 else 0.0,
            position_size_pct=position_pct,
            risk_per_share=risk_per_share,
            reward_per_share=reward_per_share,
            risk_reward_ratio=rr_ratio,
            kelly_fraction=kelly,
            half_kelly=half_kelly,
            trailing_stop_activation=trailing_activation,
            trailing_stop_pct=TRAILING_STOP_TRAIL_PCT,
            daily_max_loss_r=daily_max_loss_r,
            max_consecutive_losses=max_consecutive_losses,
            cooldown_required=risk_state.consecutive_losses >= max_consecutive_losses,
        ),
        risk_state=risk_state,
        allowed=allowed,
        block_reason=block_reason,
        suggested_position_size=shares,
        suggested_stop_loss=stop_loss,
        suggested_take_profit=take_profit,
        risk_score=risk_score,
        confidence=confidence,
    )


def update_risk_state(
    state: RiskState,
    trade_pnl: float,
    account_balance: float,
) -> RiskState:
    """Update risk state after a trade closes."""
    state.daily_pnl += trade_pnl
    state.trades_today += 1

    if trade_pnl < 0:
        state.consecutive_losses += 1
    else:
        state.consecutive_losses = 0

    state.is_cooldown = state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES
    state.is_daily_limit_hit = state.daily_pnl <= -(account_balance * DEFAULT_RISK_PER_TRADE * DAILY_MAX_LOSS_R)

    return state


def format_risk_assessment(assessment: TradeRiskAssessment) -> str:
    """Format risk assessment for display."""
    rp = assessment.risk_parameters
    lines = [
        f"=== Risk Assessment: {assessment.symbol} ===",
        f"Allowed: {assessment.allowed}",
    ]
    if assessment.block_reason:
        lines.append(f"Block Reason: {assessment.block_reason}")
    lines.extend([
        f"Entry: ${rp.entry_price:.2f}",
        f"Stop Loss: ${assessment.suggested_stop_loss:.2f} ({rp.stop_loss_pct:.1%})",
        f"Take Profit: ${assessment.suggested_take_profit:.2f} ({rp.take_profit_pct:.1%})",
        f"Risk/Reward: {rp.risk_reward_ratio:.2f}",
        f"Position Size: {assessment.suggested_position_size:.0f} shares ({rp.position_size_pct:.1%})",
        f"Kelly Fraction: {rp.kelly_fraction:.3f} (half-Kelly: {rp.half_kelly:.3f})",
        f"Trailing Stop Activates: ${rp.trailing_stop_activation:.2f}",
        f"Daily Max Loss: {rp.daily_max_loss_r:.1f}R",
        f"Consecutive Losses: {assessment.risk_state.consecutive_losses}/{rp.max_consecutive_losses}",
        f"Risk Score: {assessment.risk_score:.2f}",
        f"Confidence: {assessment.confidence:.2f}",
    ])
    return "\n".join(lines)


def build_candidate_risk_record(
    symbol: str,
    entry_price: float,
    current_price: float,
    account_balance: float,
    win_rate: float = 0.5,
    avg_win_pct: float = 0.04,
    avg_loss_pct: float = 0.02,
    atr: float | None = None,
    risk_state: RiskState | None = None,
    risk_per_trade: float | None = None,
    max_single_position_pct: float | None = None,
    max_total_exposure_pct: float | None = None,
    max_consecutive_losses: int | None = None,
    daily_max_loss_r: float | None = None,
    default_stop_loss_pct: float | None = None,
) -> dict[str, Any]:
    """Build a risk record dict for pipeline integration."""
    _rpt = risk_per_trade if risk_per_trade is not None else DEFAULT_RISK_PER_TRADE
    _mspp = max_single_position_pct if max_single_position_pct is not None else MAX_SINGLE_POSITION_PCT
    _mtep = max_total_exposure_pct if max_total_exposure_pct is not None else MAX_TOTAL_EXPOSURE_PCT
    _mcl = max_consecutive_losses if max_consecutive_losses is not None else MAX_CONSECUTIVE_LOSSES
    _dmr = daily_max_loss_r if daily_max_loss_r is not None else DAILY_MAX_LOSS_R
    _dsl = default_stop_loss_pct if default_stop_loss_pct is not None else 0.02
    assessment = assess_trade_risk(
        symbol=symbol,
        entry_price=entry_price,
        current_price=current_price,
        account_balance=account_balance,
        win_rate=win_rate,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        atr=atr,
        risk_state=risk_state,
        risk_per_trade=_rpt,
        default_stop_loss_pct=_dsl,
        max_single_position_pct=_mspp,
        max_total_exposure_pct=_mtep,
        max_consecutive_losses=_mcl,
        daily_max_loss_r=_dmr,
    )
    rp = assessment.risk_parameters
    position_size_pct = rp.position_size_pct
    shares = assessment.suggested_position_size
    if position_size_pct > _mspp and entry_price > 0 and account_balance > 0:
        position_size_pct = _mspp
        shares = (account_balance * position_size_pct) / entry_price
    position_size_value = shares * entry_price if entry_price > 0 else 0.0
    if account_balance > 0:
        position_size_pct = position_size_value / account_balance
    return {
        "symbol": symbol,
        "risk_allowed": assessment.allowed,
        "risk_block_reason": assessment.block_reason,
        "risk_pass_is_not_buy": True,
        "research_candidate_condition": True,
        "entry_price": rp.entry_price,
        "stop_loss": assessment.suggested_stop_loss,
        "stop_loss_pct": rp.stop_loss_pct,
        "take_profit": assessment.suggested_take_profit,
        "take_profit_pct": rp.take_profit_pct,
        "risk_reward_ratio": rp.risk_reward_ratio,
        "position_size_shares": shares,
        "position_size_value": position_size_value,
        "position_size_pct": position_size_pct,
        "kelly_fraction": rp.kelly_fraction,
        "half_kelly": rp.half_kelly,
        "trailing_stop_activation": rp.trailing_stop_activation,
        "trailing_stop_pct": rp.trailing_stop_pct,
        "daily_max_loss_r": _dmr,
        "max_consecutive_losses": _mcl,
        "cooldown_required": rp.cooldown_required,
        "risk_score": assessment.risk_score,
        "confidence": assessment.confidence,
        "daily_pnl": assessment.risk_state.daily_pnl,
        "consecutive_losses": assessment.risk_state.consecutive_losses,
        "total_exposure_pct": assessment.risk_state.total_exposure_pct,
    }
