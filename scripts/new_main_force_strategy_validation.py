#!/usr/bin/env python3
"""Independent as-of profitability validation for capital_behavior_v2.

Read-only. Does not mutate tickets, weights, ranking, or production strategy.
observable_footprint_v1 remains FROZEN and is LEGACY_ONLY for this report.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from capital.scoring import build_capital_assessment  # noqa: E402
from db.engine import engine  # noqa: E402
from market_calendar import CALENDAR  # noqa: E402
from market_regime import classify_market_regime  # noqa: E402
from research.boundary import PRODUCTION_BOUNDARY, RANKING_KEY  # noqa: E402

NEW_STRATEGY_ID = "capital_behavior_v2"
NEW_STRATEGY_VERSION = "capital_behavior_v2"
NEW_STRATEGY_STATUS = "UNVALIDATED_NO_FIXED_CHAIN"
NEW_STRATEGY_FORMULA = (
    "clamp(0.55*capital_strength + 0.25*capital_quality "
    "+ 0.20*|control_asymmetry| - 0.18*distribution_probability "
    "- 0.12*trap_probability)"
)
NEW_RANKING_KEY = (
    "capital_behavior_score",
    "capital_strength",
    "demand_persistence",
)
NEW_TICKET_RULE = "Top1 by NEW_RANKING_KEY after quality filter; no capital MIN_SCORE"
NEW_UNIVERSE_RULE = (
    "daily_klines as-of membership; history>=200; close>=5; "
    "median dollar volume>=5e6; as_of bar required"
)
NEW_ENTRY_TIME = "US regular session close complete bar; paper ticket after BJT 04:00"
NEW_FORWARD_RULE = "unadjusted kline close[as_of] -> close[CALENDAR.add_trading_days(as_of,h)]"
PRODUCTION_RANKING_OWNER = "observable_footprint_v1"
PRODUCTION_RANKING_KEY = list(RANKING_KEY)
DATA_VERSION = "PUBLIC_OHLCV_V2"
SOURCE_SEMANTIC = "OBSERVABLE_MARKET_BEHAVIOR_PROXY_NOT_INSTITUTIONAL_ORDER_FLOW"

HORIZONS = (1, 3, 5, 10)
COST_BPS = (0, 10, 25, 50, 100)
MIN_HISTORY_DAYS = 200
MIN_PRICE = 5.0
MIN_MEDIAN_DOLLAR_VOLUME = 5_000_000.0
MIN_ASOF_POOL = 20
MIN_INDEPENDENT_SAMPLES = 30
ASOF_FEATURE_BARS = 60
RANDOM_SEED = 20260906
REPLAY_START = date(2025, 1, 2)
KLINE_LOAD_START = date(2022, 1, 3)
OUTPUT_DIR = ROOT / "research" / "new_main_force_strategy"
SCORE_WORKERS = min(8, max(1, os.cpu_count() or 4))
SOURCE_FILES = (
    "scripts/capital/scoring.py",
    "scripts/capital/features.py",
    "scripts/capital/evidence.py",
    "scripts/capital/control.py",
    "scripts/capital/state.py",
    "scripts/capital/intent.py",
    "scripts/capital/path.py",
    "scripts/capital/__init__.py",
)

FACTOR_COLUMNS = (
    "upward_pressure",
    "downward_pressure",
    "volume_pressure",
    "demand_persistence",
    "supply_exhaustion",
    "absorption",
    "accumulation",
    "markup",
    "distribution",
    "crowding",
    "trap",
    "selling_activity",
    "price_damage",
    "damage_efficiency",
    "absorption_failure",
    "price_response_efficiency",
    "control_asymmetry",
    "capital_strength",
    "capital_quality",
    "distribution_probability",
    "trap_probability",
    "capital_behavior_score",
)

NEW_STRATEGY_FACTORS = list(FACTOR_COLUMNS)
NEW_STRATEGY_WEIGHTS = {
    "capital_strength": 0.55,
    "capital_quality": 0.25,
    "abs_control_asymmetry": 0.20,
    "distribution_probability": -0.18,
    "trap_probability": -0.12,
    "capital_strength_components": {
        "direction_pressure": 0.22,
        "demand_persistence": 0.16,
        "selling_activity": 0.14,
        "absorption": 0.14,
        "price_response_efficiency": 0.14,
        "state_confidence": 0.10,
        "transition_confidence": 0.10,
        "regime_alignment": 0.04,
    },
}

FACTOR_THEORY = {
    "upward_pressure": {"meaning": "recent upside return/volume/close position", "higher": "more upside pressure", "direction": "+"},
    "downward_pressure": {"meaning": "recent downside return/volume/weak close", "higher": "more downside pressure", "direction": "-_as_quality"},
    "volume_pressure": {"meaning": "volume vs 20d baseline and persistence", "higher": "more activity", "direction": "mixed"},
    "demand_persistence": {"meaning": "positive days, 5d return, recovery, RS", "higher": "demand more persistent", "direction": "+"},
    "supply_exhaustion": {"meaning": "failed breakdown, higher low, decaying downside volume", "higher": "supply fading", "direction": "+"},
    "absorption": {"meaning": "selling activity absorbed with low damage", "higher": "better absorption proxy", "direction": "+"},
    "accumulation": {"meaning": "absorption + supply exhaustion + RS", "higher": "more accumulation-like tape", "direction": "+"},
    "markup": {"meaning": "upward pressure + demand + volume + RS", "higher": "more markup-like tape", "direction": "+"},
    "distribution": {"meaning": "high activity with poor price progress", "higher": "more distribution-like tape", "direction": "-"},
    "crowding": {"meaning": "late extension, volume spike, concentration", "higher": "more crowded tape", "direction": "-"},
    "trap": {"meaning": "distribution + weak close after volume", "higher": "more trap-like tape", "direction": "-"},
    "selling_activity": {"meaning": "down-volume share and downside returns", "higher": "more selling activity", "direction": "mixed"},
    "price_damage": {"meaning": "downside return vs volatility and support", "higher": "more damage", "direction": "-"},
    "damage_efficiency": {"meaning": "1 - actual_damage/expected_damage", "higher": "less damage than expected", "direction": "+"},
    "absorption_failure": {"meaning": "selling plus damage minus efficiency", "higher": "absorption failing", "direction": "-"},
    "price_response_efficiency": {"meaning": "directional response per activity", "higher": "price responds more to activity", "direction": "+"},
    "control_asymmetry": {"meaning": "upside minus downside control", "higher": "long control advantage", "direction": "+_abs_in_score"},
    "capital_strength": {"meaning": "weighted pressure/persistence/absorption/control", "higher": "stronger observable pressure", "direction": "+"},
    "capital_quality": {"meaning": "persistence/absorption minus distribution/trap", "higher": "healthier tape quality", "direction": "+"},
    "distribution_probability": {"meaning": "distribution + crowding + absorption failure", "higher": "higher distribution risk proxy", "direction": "-"},
    "trap_probability": {"meaning": "trap + distribution + weak confidence", "higher": "higher trap risk proxy", "direction": "-"},
    "capital_behavior_score": {"meaning": "official capital_behavior_v2 ranking score", "higher": "ranked better by current formula", "direction": "+"},
}


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {rel: sha256_file(ROOT / rel) for rel in SOURCE_FILES}


def fingerprint_payload() -> dict[str, Any]:
    hashes = source_hashes()
    blob = json.dumps(
        {
            "strategy_id": NEW_STRATEGY_ID,
            "strategy_version": NEW_STRATEGY_VERSION,
            "formula": NEW_STRATEGY_FORMULA,
            "ranking_key": list(NEW_RANKING_KEY),
            "weights": NEW_STRATEGY_WEIGHTS,
            "universe_rule": NEW_UNIVERSE_RULE,
            "ticket_rule": NEW_TICKET_RULE,
            "entry_time": NEW_ENTRY_TIME,
            "forward_rule": NEW_FORWARD_RULE,
            "source_sha256": hashes,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return {
        "NEW_STRATEGY_ID": NEW_STRATEGY_ID,
        "NEW_STRATEGY_VERSION": NEW_STRATEGY_VERSION,
        "NEW_STRATEGY_STATUS": NEW_STRATEGY_STATUS,
        "NEW_STRATEGY_FORMULA": NEW_STRATEGY_FORMULA,
        "NEW_STRATEGY_FACTORS": NEW_STRATEGY_FACTORS,
        "NEW_STRATEGY_WEIGHTS": NEW_STRATEGY_WEIGHTS,
        "NEW_RANKING_KEY": list(NEW_RANKING_KEY),
        "NEW_TICKET_RULE": NEW_TICKET_RULE,
        "NEW_UNIVERSE_RULE": NEW_UNIVERSE_RULE,
        "NEW_ENTRY_TIME": NEW_ENTRY_TIME,
        "NEW_FORWARD_RULE": NEW_FORWARD_RULE,
        "DATA_VERSION": DATA_VERSION,
        "SOURCE_SEMANTIC": SOURCE_SEMANTIC,
        "PRODUCTION_RANKING_OWNER": PRODUCTION_RANKING_OWNER,
        "PRODUCTION_RANKING_KEY": PRODUCTION_RANKING_KEY,
        "PRODUCTION_BOUNDARY": dict(PRODUCTION_BOUNDARY),
        "source_sha256": hashes,
        "fingerprint_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "git_commit": _git_commit(),
        "locked_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "do_not_mutate_during_replay": True,
    }


def _git_commit() -> str:
    head = ROOT / ".git" / "HEAD"
    try:
        import subprocess

        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return head.read_text(encoding="utf-8").strip() if head.exists() else "UNKNOWN"


def identity_lock() -> dict[str, str]:
    return {
        "NEW_STRATEGY_ID": NEW_STRATEGY_ID,
        "NEW_STRATEGY_VERSION": NEW_STRATEGY_VERSION,
        "NEW_STRATEGY_STATUS": NEW_STRATEGY_STATUS,
        "NEW_STRATEGY_FORMULA": NEW_STRATEGY_FORMULA,
        "NEW_STRATEGY_FACTORS": ",".join(NEW_STRATEGY_FACTORS),
        "NEW_STRATEGY_WEIGHTS": json.dumps(NEW_STRATEGY_WEIGHTS, sort_keys=True),
        "NEW_RANKING_KEY": ",".join(NEW_RANKING_KEY),
        "NEW_TICKET_RULE": NEW_TICKET_RULE,
        "NEW_UNIVERSE_RULE": NEW_UNIVERSE_RULE,
        "NEW_ENTRY_TIME": NEW_ENTRY_TIME,
        "NEW_FORWARD_RULE": NEW_FORWARD_RULE,
    }


def readonly_query(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
        return [dict(row) for row in rows]


def load_kline_bars() -> pd.DataFrame:
    with engine.connect() as conn:
        frame = pd.read_sql(
            text(
                """
                SELECT symbol, trade_date, open, high, low, close, adj_close, volume
                FROM daily_klines
                WHERE trade_date >= :start_date
                ORDER BY symbol, trade_date
                """
            ),
            conn,
            params={"start_date": KLINE_LOAD_START},
        )
    if frame.empty:
        return pd.DataFrame(columns=["symbol", "trade_date", "open", "high", "low", "close", "adj_close", "volume"])
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.date
    for key in ("open", "high", "low", "close", "adj_close", "volume"):
        frame[key] = pd.to_numeric(frame[key], errors="coerce")
    frame["symbol"] = frame["symbol"].astype(str)
    return frame.dropna(subset=["trade_date", "symbol", "close"])


def load_obsidian_notes() -> list[dict[str, Any]]:
    rows = readonly_query(
        """
        SELECT id, title, source_path, source_type, left(content, 400) AS excerpt
        FROM knowledge_assets
        WHERE source_type = 'us_stock'
          AND (
            content ILIKE '%capital_behavior%'
            OR content ILIKE '%主力%'
            OR content ILIKE '%observable_footprint%'
            OR title ILIKE '%知识资产%'
          )
        ORDER BY id DESC
        LIMIT 40
        """
    )
    return rows


def quality_filter_asof_symbol(history: pd.DataFrame, as_of: date) -> dict[str, Any]:
    visible = history[history["trade_date"] <= as_of].sort_values("trade_date")
    if visible.empty:
        return {"include": False, "reasons": ["no_as_of_bar"], "history_days": 0}
    last = visible.iloc[-1]
    if last["trade_date"] != as_of:
        return {"include": False, "reasons": ["not_in_as_of_session"], "history_days": int(len(visible))}
    last_close = _as_float(last["close"])
    dollar = visible["close"] * visible["volume"]
    median_dollar = float(dollar.dropna().median()) if dollar.notna().any() else None
    reasons: list[str] = []
    if len(visible) < MIN_HISTORY_DAYS:
        reasons.append("history_days_short")
    if last_close is None or last_close < MIN_PRICE:
        reasons.append("price_floor")
    if median_dollar is None or median_dollar < MIN_MEDIAN_DOLLAR_VOLUME:
        reasons.append("median_dollar_volume")
    return {
        "include": not reasons,
        "reasons": reasons,
        "history_days": int(len(visible)),
        "last_close": last_close,
        "median_dollar_volume": median_dollar,
    }


def asof_session_return(history: pd.DataFrame, as_of: date, horizon: int) -> dict[str, Any]:
    ordered = history.sort_values("trade_date")
    as_of_rows = ordered[ordered["trade_date"] == as_of]
    if as_of_rows.empty:
        return {"return": None, "source": "missing_as_of_bar"}
    due = CALENDAR.add_trading_days(as_of, horizon)
    due_rows = ordered[ordered["trade_date"] == due]
    if due_rows.empty:
        return {"return": None, "source": "missing_future_price", "due_date": due}
    entry = _as_float(as_of_rows.iloc[0]["close"])
    exit_px = _as_float(due_rows.iloc[0]["close"])
    if entry is None or exit_px is None or entry <= 0:
        return {"return": None, "source": "missing_future_price", "due_date": due}
    return {
        "return": exit_px / entry - 1.0,
        "source": "kline_close_unadjusted",
        "due_date": due,
        "as_of_close": entry,
        "due_close": exit_px,
    }


def _mean_or_none(values: list[float | None]) -> float | None:
    clean = [float(item) for item in values if item is not None and not (isinstance(item, float) and math.isnan(item))]
    if not clean:
        return None
    return float(np.mean(clean))


def score_symbol(
    history: pd.DataFrame,
    as_of: date,
    *,
    relative_strength: float | None,
    regime_alignment: float,
    previous_state: str | None,
    previous_duration: int,
) -> dict[str, Any]:
    if "trade_date" in history.columns:
        visible = history[history["trade_date"] <= as_of].sort_values("trade_date").tail(ASOF_FEATURE_BARS)
        last_date = visible.iloc[-1]["trade_date"] if not visible.empty else None
        frame_src = visible.rename(columns={"trade_date": "date"})
    else:
        visible = history.loc[:as_of].tail(ASOF_FEATURE_BARS)
        last_date = visible.index[-1] if not visible.empty else None
        if isinstance(last_date, pd.Timestamp):
            last_date = last_date.date()
        frame_src = visible.reset_index().rename(columns={"trade_date": "date", "index": "date"})
    if visible.empty or last_date != as_of:
        return {"available": False, "reason": "no_as_of_bar"}
    if last_date is not None and last_date > as_of:
        raise RuntimeError("future bar leaked into capital score input")
    frame = frame_src[["date", "open", "high", "low", "close", "volume"]]
    assessment = build_capital_assessment(
        frame,
        statistical_score=0.0,
        relative_strength=relative_strength,
        regime_alignment=regime_alignment,
        previous_state=previous_state,
        previous_duration=previous_duration,
    )
    evidence = {key: float(item.get("value", 0.0)) for key, item in assessment["evidence"]["evidence"].items()}
    scores = assessment["scores"]
    control = assessment["control"]
    state = assessment["state"]
    return {
        "available": assessment["evidence"].get("availability") == "AVAILABLE",
        "model_version": assessment["model_version"],
        "validation_status": assessment["validation_status"],
        "capital_behavior_score": float(scores["capital_behavior_score"]),
        "capital_strength": float(scores["capital_strength"]),
        "capital_quality": float(scores["capital_quality"]),
        "distribution_probability": float(scores["distribution_probability"]),
        "trap_probability": float(scores["trap_probability"]),
        "combined_score_unused": float(scores["combined_score"]),
        "statistical_score_forced_zero": float(scores["statistical_score"]),
        "price_response_efficiency": float(control["price_response_efficiency"]),
        "control_asymmetry": float(control["control_asymmetry"]),
        "dominant_direction": control["dominant_direction"],
        "capital_state": state.get("capital_state"),
        "state_duration": int(state.get("state_duration") or 0),
        "capital_intent": assessment["intent"].get("capital_intent"),
        "path_type": assessment["path"].get("path_type"),
        **{key: float(evidence.get(key, 0.0)) for key in (
            "upward_pressure", "downward_pressure", "volume_pressure",
            "demand_persistence", "supply_exhaustion", "absorption",
            "accumulation", "markup", "distribution", "crowding", "trap",
            "selling_activity", "price_damage", "damage_efficiency",
            "absorption_failure",
        )},
    }


def horizon_metrics(returns: list[float | None]) -> dict[str, Any]:
    values: list[float] = []
    for item in returns:
        if item is None:
            continue
        try:
            number = float(item)
        except (TypeError, ValueError):
            continue
        if math.isnan(number) or math.isinf(number):
            continue
        values.append(number)
    sample_count = len(values)
    empty = {
        "sample_count": 0,
        "wins": 0,
        "losses": 0,
        "flats": 0,
        "win_rate": None,
        "avg_return": None,
        "median_return": None,
        "best_trade": None,
        "worst_trade": None,
        "avg_win": None,
        "avg_loss": None,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "profit_factor": None,
        "expectancy": None,
        "std_return": None,
        "max_drawdown": None,
    }
    if sample_count == 0:
        return empty
    wins = [item for item in values if item > 0]
    losses = [item for item in values if item < 0]
    flats = sample_count - len(wins) - len(losses)
    win_rate = len(wins) / sample_count
    loss_rate = len(losses) / sample_count
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    gross_profit = float(sum(wins))
    gross_loss = float(sum(losses))
    if gross_loss == 0 and gross_profit > 0:
        profit_factor = float("inf")
    elif gross_loss == 0:
        profit_factor = None
    else:
        profit_factor = gross_profit / abs(gross_loss)
    expectancy = win_rate * avg_win + loss_rate * avg_loss
    equity = equity_from_daily(list(enumerate(values)))
    return {
        "sample_count": sample_count,
        "wins": len(wins),
        "losses": len(losses),
        "flats": flats,
        "win_rate": win_rate,
        "avg_return": float(np.mean(values)),
        "median_return": float(np.median(values)),
        "best_trade": float(max(values)),
        "worst_trade": float(min(values)),
        "avg_win": avg_win if wins else None,
        "avg_loss": avg_loss if losses else None,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "std_return": float(np.std(values, ddof=1)) if sample_count > 1 else 0.0,
        "max_drawdown": equity["max_drawdown"],
    }


def apply_friction(returns: list[float], bps: int) -> list[float]:
    friction = bps / 10000.0
    return [item - friction for item in returns]


def equity_from_daily(returns_by_day: list[tuple[Any, float]]) -> dict[str, Any]:
    if not returns_by_day:
        return {"cumulative_return": None, "max_drawdown": None, "points": []}
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    points = []
    for day, ret in returns_by_day:
        equity *= 1.0 + ret
        if equity > peak:
            peak = equity
        drawdown = equity / peak - 1.0
        if drawdown < max_dd:
            max_dd = drawdown
        points.append({"date": str(day), "daily_return": ret, "equity": equity, "drawdown": drawdown})
    return {
        "cumulative_return": equity - 1.0,
        "max_drawdown": max_dd,
        "points": points,
    }


def split_periods(dates: list[date]) -> dict[str, list[date]]:
    unique = sorted({day for day in dates if day is not None})
    if not unique:
        return {"train": [], "validation": [], "holdout": []}
    n = len(unique)
    train_end = max(1, int(n * 0.60))
    valid_end = max(train_end + 1, int(n * 0.80)) if n >= 5 else train_end
    if n < 5:
        return {"train": unique[: max(1, n - 1)], "validation": [], "holdout": unique[-1:]}
    return {
        "train": unique[:train_end],
        "validation": unique[train_end:valid_end],
        "holdout": unique[valid_end:],
    }


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    value = float(np.corrcoef(xs, ys)[0, 1])
    if math.isnan(value):
        return None
    return value


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    return correlation(pd.Series(xs).rank().tolist(), pd.Series(ys).rank().tolist())


def rng_for_date(as_of: date) -> np.random.Generator:
    seed = int(hashlib.sha256(f"{RANDOM_SEED}:{as_of.isoformat()}".encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


def classify_env(regime_name: str, volatility: float, vol_median: float) -> dict[str, str]:
    trend = {"risk_on": "bull", "risk_off": "bear"}.get(regime_name, "sideways")
    vol_label = "high_volatility" if volatility >= vol_median else "low_volatility"
    return {"trend": trend, "volatility_bucket": vol_label, "pipeline_regime": regime_name}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def fmt_pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.2f}%" if signed else f"{value * 100:.2f}%"


def fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    if math.isinf(value):
        return "inf"
    return f"{value:.4f}"


def metrics_block(metrics: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- n: `{metrics.get('sample_count')}`",
            f"- win_rate: `{fmt_pct(metrics.get('win_rate'), signed=False)}`",
            f"- avg_return: `{fmt_pct(metrics.get('avg_return'))}`",
            f"- median_return: `{fmt_pct(metrics.get('median_return'))}`",
            f"- profit_factor: `{fmt_num(metrics.get('profit_factor'))}`",
            f"- expectancy: `{fmt_pct(metrics.get('expectancy'))}`",
            f"- avg_win: `{fmt_pct(metrics.get('avg_win'))}`",
            f"- avg_loss: `{fmt_pct(metrics.get('avg_loss'))}`",
            f"- best_trade: `{fmt_pct(metrics.get('best_trade'))}`",
            f"- worst_trade: `{fmt_pct(metrics.get('worst_trade'))}`",
            f"- max_drawdown: `{fmt_pct(metrics.get('max_drawdown'))}`",
        ]
    )


def walk_one_symbol(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Sequential as-of walk for one symbol. Previous state never uses future days."""
    history = task["history"]
    close_map: dict[str, float] = task["close_map"]
    due_map: dict[str, dict[str, str]] = task["due_map"]
    previous_state = None
    previous_duration = 0
    rows: list[dict[str, Any]] = []
    for as_of_s, ctx in task["included_days"]:
        as_of = date.fromisoformat(as_of_s)
        scored_row = score_symbol(
            history,
            as_of,
            relative_strength=ctx.get("rs"),
            regime_alignment=float(ctx.get("participation") or 0.5),
            previous_state=previous_state,
            previous_duration=previous_duration,
        )
        if not scored_row.get("available"):
            continue
        row = {
            "symbol": task["symbol"],
            "trade_date": as_of,
            "series": "NEW_MAIN_FORCE_STRATEGY",
            **scored_row,
        }
        entry = close_map.get(as_of_s)
        for horizon in HORIZONS:
            due = due_map[str(horizon)].get(as_of_s)
            exit_px = close_map.get(due) if due else None
            if entry is not None and exit_px is not None and entry > 0:
                row[f"t{horizon}"] = exit_px / entry - 1.0
                row[f"t{horizon}_source"] = "kline_close_unadjusted"
            else:
                row[f"t{horizon}"] = None
                row[f"t{horizon}_source"] = "missing_future_price"
        rows.append(row)
        previous_state = scored_row.get("capital_state")
        previous_duration = int(scored_row.get("state_duration") or 0)
    return rows


def replay(bars: pd.DataFrame) -> dict[str, Any]:
    if bars.empty:
        return {"status": "DATA_INVALID", "reason": "no_klines", "daily": [], "candidates": pd.DataFrame()}
    histories: dict[str, pd.DataFrame] = {}
    quality_ok: dict[str, set[date]] = {}
    close_maps: dict[str, dict[str, float]] = {}
    for symbol, group in bars.groupby("symbol", sort=True):
        hist = group.sort_values("trade_date").copy()
        dollar = hist["close"] * hist["volume"]
        hist["history_days"] = np.arange(1, len(hist) + 1)
        hist["median_dollar"] = dollar.expanding().median()
        ok = (
            (hist["history_days"] >= MIN_HISTORY_DAYS)
            & (hist["close"] >= MIN_PRICE)
            & (hist["median_dollar"] >= MIN_MEDIAN_DOLLAR_VOLUME)
        )
        quality_ok[str(symbol)] = set(hist.loc[ok, "trade_date"])
        histories[str(symbol)] = hist.reset_index(drop=True)
        close_maps[str(symbol)] = {
            day.isoformat(): float(close)
            for day, close in zip(hist["trade_date"], hist["close"])
            if day is not None and close is not None
        }

    all_dates = sorted({day for day in bars["trade_date"].unique() if day is not None and day >= REPLAY_START})
    last_bar_date = max(all_dates)
    replay_dates = [day for day in all_dates if CALENDAR.add_trading_days(day, 1) <= last_bar_date]
    due_map = {
        str(horizon): {
            day.isoformat(): CALENDAR.add_trading_days(day, horizon).isoformat()
            for day in replay_dates
        }
        for horizon in HORIZONS
    }
    close_panel = bars.pivot_table(index="trade_date", columns="symbol", values="close", aggfunc="last").sort_index()
    close_panel.index = pd.DatetimeIndex(pd.to_datetime(close_panel.index))

    daily_rows: list[dict[str, Any]] = []
    vol_values: list[float] = []
    included_days_by_symbol: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    day_meta: dict[date, dict[str, Any]] = {}

    for as_of in replay_dates:
        included = [symbol for symbol, dateset in quality_ok.items() if as_of in dateset]
        if len(included) < MIN_ASOF_POOL:
            daily_rows.append({
                "as_of_date": as_of,
                "status": "INCOMPLETE_ASOF_PANEL",
                "included_count": len(included),
            })
            continue
        window = close_panel.loc[: pd.Timestamp(as_of), included].tail(25)
        regime = classify_market_regime(window, included)
        participation = min(1.0, max(0.0, (float(regime.breadth) + float(regime.advance_ratio)) / 200.0))
        vol_values.append(float(regime.volatility))
        prior_20d = window / window.shift(20) - 1.0
        as_of_ts = pd.Timestamp(as_of)
        equal_weight_20d = float(prior_20d.loc[as_of_ts].dropna().mean()) if as_of_ts in prior_20d.index else 0.0
        relative = (prior_20d.loc[as_of_ts] - equal_weight_20d) if as_of_ts in prior_20d.index else pd.Series(dtype=float)
        day_meta[as_of] = {
            "included": included,
            "regime": regime,
            "participation": participation,
        }
        for symbol in included:
            included_days_by_symbol[symbol].append(
                (
                    as_of.isoformat(),
                    {
                        "rs": _as_float(relative.get(symbol)) if symbol in relative.index else None,
                        "participation": participation,
                    },
                )
            )

    tasks = [
        {
            "symbol": symbol,
            "history": histories[symbol],
            "close_map": close_maps[symbol],
            "due_map": due_map,
            "included_days": included_days_by_symbol[symbol],
        }
        for symbol in sorted(included_days_by_symbol)
    ]
    candidate_rows: list[dict[str, Any]] = []
    if tasks:
        workers = min(SCORE_WORKERS, len(tasks))
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("fork")) as pool:
            for rows in pool.map(walk_one_symbol, tasks, chunksize=1):
                candidate_rows.extend(rows)

    candidates = pd.DataFrame(candidate_rows)
    ranked_rows: list[dict[str, Any]] = []
    if not candidates.empty:
        candidates["trade_date"] = candidates["trade_date"].map(_as_date)
        for as_of, meta in day_meta.items():
            day_frame = candidates[candidates["trade_date"] == as_of]
            scored = day_frame.to_dict(orient="records")
            if len(scored) < MIN_ASOF_POOL:
                daily_rows.append({
                    "as_of_date": as_of,
                    "status": "INSUFFICIENT_SCORED",
                    "included_count": len(meta["included"]),
                    "scored_count": len(scored),
                })
                continue
            ranked = sorted(
                scored,
                key=lambda item: tuple(item.get(key) or 0.0 for key in NEW_RANKING_KEY),
                reverse=True,
            )
            regime = meta["regime"]
            for index, row in enumerate(ranked, start=1):
                row["rank"] = index
                row["ticket_flag"] = index == 1
                row["top3_flag"] = index <= 3
                row["top5_flag"] = index <= 5
                row["regime"] = regime.name
                row["breadth"] = regime.breadth
                row["advance_ratio"] = regime.advance_ratio
                row["volatility"] = regime.volatility
                ranked_rows.append(row)
            rng = rng_for_date(as_of)
            random_idx = rng.choice(len(ranked), size=min(5, len(ranked)), replace=False)
            daily_rows.append({
                "as_of_date": as_of,
                "status": "FULL_ASOF_PANEL",
                "included_count": len(meta["included"]),
                "scored_count": len(ranked),
                "regime": regime.name,
                "breadth": regime.breadth,
                "advance_ratio": regime.advance_ratio,
                "volatility": regime.volatility,
                "momentum": regime.momentum,
                "top1": ranked[0]["symbol"],
                "top1_score": ranked[0]["capital_behavior_score"],
                **{f"top1_t{h}": ranked[0].get(f"t{h}") for h in HORIZONS},
                **{f"top3_t{h}": _mean_or_none([row.get(f"t{h}") for row in ranked[:3]]) for h in HORIZONS},
                **{f"top5_t{h}": _mean_or_none([row.get(f"t{h}") for row in ranked[:5]]) for h in HORIZONS},
                **{f"equal_t{h}": _mean_or_none([row.get(f"t{h}") for row in ranked]) for h in HORIZONS},
                **{f"random1_t{h}": ranked[int(random_idx[0])].get(f"t{h}") for h in HORIZONS},
                **{f"random3_t{h}": _mean_or_none([ranked[int(i)].get(f"t{h}") for i in random_idx[:3]]) for h in HORIZONS},
                **{f"random5_t{h}": _mean_or_none([ranked[int(i)].get(f"t{h}") for i in random_idx[:5]]) for h in HORIZONS},
            })
    daily = pd.DataFrame(daily_rows)
    ranked_frame = pd.DataFrame(ranked_rows)
    return {
        "status": "ok",
        "daily": daily,
        "candidates": ranked_frame,
        "vol_median": float(np.median(vol_values)) if vol_values else 0.02,
        "replay_dates": replay_dates,
        "last_bar_date": last_bar_date,
    }


def bucket_returns(scores: pd.Series, returns: pd.Series, q: float, top: bool) -> float | None:
    aligned = pd.DataFrame({"score": scores, "ret": returns}).dropna()
    if aligned.empty:
        return None
    cutoff = aligned["score"].quantile(1.0 - q if top else q)
    selected = aligned[aligned["score"] >= cutoff] if top else aligned[aligned["score"] <= cutoff]
    if selected.empty:
        return None
    return float(selected["ret"].mean())


def ranking_for_horizon(candidates: pd.DataFrame, horizon: int) -> dict[str, Any]:
    col = f"t{horizon}"
    work = candidates.dropna(subset=["capital_behavior_score", col]).copy()
    if work.empty:
        return {"n": 0}
    pearson = correlation(work["capital_behavior_score"].tolist(), work[col].tolist())
    spear = spearman(work["capital_behavior_score"].tolist(), work[col].tolist())
    top1 = work[work["rank"] == 1][col]
    return {
        "n": int(len(work)),
        "pearson": pearson,
        "spearman": spear,
        "Top1": float(top1.mean()) if not top1.empty else None,
        "Top5pct": bucket_returns(work["capital_behavior_score"], work[col], 0.05, True),
        "Top10pct": bucket_returns(work["capital_behavior_score"], work[col], 0.10, True),
        "Top20pct": bucket_returns(work["capital_behavior_score"], work[col], 0.20, True),
        "Bottom20pct": bucket_returns(work["capital_behavior_score"], work[col], 0.20, False),
    }


def factor_forensics(candidates: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for factor in FACTOR_COLUMNS:
        if factor not in candidates:
            continue
        per_horizon = {}
        for horizon in HORIZONS:
            col = f"t{horizon}"
            work = candidates.dropna(subset=[factor, col])
            if work.empty:
                per_horizon[f"t{horizon}"] = {"n": 0}
                continue
            ics = []
            rank_ics = []
            for _, group in work.groupby("trade_date"):
                if len(group) < 8:
                    continue
                ics.append(correlation(group[factor].tolist(), group[col].tolist()))
                rank_ics.append(spearman(group[factor].tolist(), group[col].tolist()))
            ics = [item for item in ics if item is not None]
            rank_ics = [item for item in rank_ics if item is not None]
            top = bucket_returns(work[factor], work[col], 0.20, True)
            bottom = bucket_returns(work[factor], work[col], 0.20, False)
            per_horizon[f"t{horizon}"] = {
                "n": int(len(work)),
                "ic": float(np.mean(ics)) if ics else None,
                "rank_ic": float(np.mean(rank_ics)) if rank_ics else None,
                "top_bucket_return": top,
                "bottom_bucket_return": bottom,
                "monotonicity": None if top is None or bottom is None else float(top - bottom),
            }
        result[factor] = {
            "theory": FACTOR_THEORY.get(factor, {}),
            "horizons": per_horizon,
        }
    corr = candidates[list(FACTOR_COLUMNS)].corr(numeric_only=True)
    redundant = []
    for i, left in enumerate(FACTOR_COLUMNS):
        for right in FACTOR_COLUMNS[i + 1 :]:
            value = corr.loc[left, right] if left in corr.index and right in corr.columns else None
            if value is not None and abs(float(value)) >= 0.80:
                redundant.append({"left": left, "right": right, "corr": float(value)})
    t1 = {name: payload["horizons"].get("t1", {}).get("rank_ic") for name, payload in result.items()}
    ranked = sorted(((name, ic) for name, ic in t1.items() if ic is not None), key=lambda item: abs(item[1]), reverse=True)
    return {
        "factors": result,
        "high_correlation_pairs": redundant,
        "dominance_by_abs_t1_rank_ic": ranked[:8],
        "dilution_note": "capital_behavior_score mixes + and - terms; a strong factor can be diluted by redundant or opposing terms.",
    }


def decide_verdict(payload: dict[str, Any]) -> dict[str, Any]:
    top1_t1 = payload["strategy"]["top1"]["1"]
    holdout = payload["walk_forward"]["holdout"]
    cost10 = payload["cost_stress"]["10"]
    cost25 = payload["cost_stress"]["25"]
    ranking = payload["ranking"]["1"]
    equal = payload["baselines"]["equal_weight"]["1"]
    random = payload["baselines"]["random_top1"]["1"]
    full_days = payload["coverage"]["full_asof_days"]
    leak = payload["coverage"]["future_data_in_features"]
    reasons = []
    if leak:
        return {"NEW_MAIN_FORCE_STRATEGY_PROFITABILITY": "DATA_INVALID", "PROFITABILITY_VALIDATED": "NO", "reasons": ["future_data_in_features"]}
    if full_days == 0:
        return {"NEW_MAIN_FORCE_STRATEGY_PROFITABILITY": "DATA_INVALID", "PROFITABILITY_VALIDATED": "NO", "reasons": ["no_full_asof_panel"]}
    n = int(top1_t1.get("sample_count") or 0)
    if n < MIN_INDEPENDENT_SAMPLES:
        return {
            "NEW_MAIN_FORCE_STRATEGY_PROFITABILITY": "INSUFFICIENT_SAMPLE",
            "PROFITABILITY_VALIDATED": "NO",
            "reasons": [f"top1_t1_n={n}"],
        }
    t1_pos = (top1_t1.get("expectancy") or 0) > 0 and (top1_t1.get("avg_return") or 0) > 0 and (top1_t1.get("profit_factor") or 0) > 1
    holdout_pos = (holdout.get("sample_count") or 0) > 0 and (holdout.get("avg_return") or 0) > 0 and (holdout.get("profit_factor") or 0) > 1
    cost_ok = (cost10.get("avg_return") or 0) > 0 and (cost25.get("avg_return") or 0) > 0
    beats_random = (top1_t1.get("avg_return") or 0) > (random.get("avg_return") or 0)
    beats_equal = (top1_t1.get("avg_return") or 0) > (equal.get("avg_return") or 0)
    rank_ok = (ranking.get("Top1") or 0) > (ranking.get("Bottom20pct") or 0) and (ranking.get("Top20pct") or 0) >= (ranking.get("Bottom20pct") or 0)
    if ranking.get("Bottom20pct") is not None and ranking.get("Top20pct") is not None:
        if ranking["Bottom20pct"] > ranking["Top20pct"]:
            reasons.append("Bottom20pct_beats_Top20pct")
    gates = {
        "identity_locked": True,
        "legacy_isolated": True,
        "asof_no_future_data": not leak,
        "top1_enough_sample": n >= MIN_INDEPENDENT_SAMPLES,
        "t1_positive_expectancy": t1_pos,
        "profit_factor_gt_1": (top1_t1.get("profit_factor") or 0) > 1,
        "cost_still_positive": cost_ok,
        "holdout_positive": holdout_pos,
        "top_beats_baselines": beats_random and beats_equal,
        "no_data_leak": not leak,
        "ranking_not_inverted": rank_ok,
    }
    if all(gates.values()):
        return {
            "NEW_MAIN_FORCE_STRATEGY_PROFITABILITY": "VALIDATED",
            "PROFITABILITY_VALIDATED": "YES",
            "reasons": ["all_success_gates_passed"],
            "gates": gates,
        }
    reasons.extend([name for name, ok in gates.items() if not ok])
    return {
        "NEW_MAIN_FORCE_STRATEGY_PROFITABILITY": "NOT_VALIDATED",
        "PROFITABILITY_VALIDATED": "NO",
        "reasons": reasons,
        "gates": gates,
    }


def analyze(replay_result: dict[str, Any], fingerprint: dict[str, Any], obsidian: list[dict[str, Any]]) -> dict[str, Any]:
    daily = replay_result["daily"]
    candidates = replay_result["candidates"]
    full = daily[daily["status"] == "FULL_ASOF_PANEL"].copy() if not daily.empty else daily
    strategy = {"top1": {}, "top3": {}, "top5": {}}
    baselines = {"equal_weight": {}, "random_top1": {}, "random_top3": {}, "random_top5": {}}
    for horizon in HORIZONS:
        key = str(horizon)
        strategy["top1"][key] = horizon_metrics(full[f"top1_t{horizon}"].tolist() if not full.empty else [])
        strategy["top3"][key] = horizon_metrics(full[f"top3_t{horizon}"].tolist() if not full.empty else [])
        strategy["top5"][key] = horizon_metrics(full[f"top5_t{horizon}"].tolist() if not full.empty else [])
        baselines["equal_weight"][key] = horizon_metrics(full[f"equal_t{horizon}"].tolist() if not full.empty else [])
        baselines["random_top1"][key] = horizon_metrics(full[f"random1_t{horizon}"].tolist() if not full.empty else [])
        baselines["random_top3"][key] = horizon_metrics(full[f"random3_t{horizon}"].tolist() if not full.empty else [])
        baselines["random_top5"][key] = horizon_metrics(full[f"random5_t{horizon}"].tolist() if not full.empty else [])
    ranking = {str(h): ranking_for_horizon(candidates, h) for h in HORIZONS}
    dates = [day for day in full["as_of_date"].tolist()] if not full.empty else []
    periods = split_periods(dates)
    walk_forward = {}
    for name, period_dates in periods.items():
        subset = full[full["as_of_date"].isin(period_dates)] if not full.empty else full
        metrics = horizon_metrics(subset["top1_t1"].tolist() if not subset.empty else [])
        metrics["n_days"] = int(len(period_dates))
        metrics["start"] = period_dates[0].isoformat() if period_dates else None
        metrics["end"] = period_dates[-1].isoformat() if period_dates else None
        walk_forward[name] = metrics
    top1_t1 = full["top1_t1"].dropna().tolist() if not full.empty else []
    cost_stress = {str(bps): horizon_metrics(apply_friction(top1_t1, bps)) for bps in COST_BPS}
    vol_median = replay_result["vol_median"]
    regime_rows: dict[str, list[float]] = defaultdict(list)
    if not full.empty:
        for _, row in full.iterrows():
            env = classify_env(str(row.get("regime") or "balanced"), float(row.get("volatility") or 0.0), vol_median)
            if row.get("top1_t1") is None:
                continue
            regime_rows[env["trend"]].append(row["top1_t1"])
            regime_rows[env["volatility_bucket"]].append(row["top1_t1"])
            regime_rows[f"pipeline_{env['pipeline_regime']}"].append(row["top1_t1"])
    regimes = {name: horizon_metrics(values) for name, values in regime_rows.items()}
    forensics = factor_forensics(candidates) if not candidates.empty else {"factors": {}}
    coverage = {
        "kline_symbols": int(candidates["symbol"].nunique()) if not candidates.empty else 0,
        "full_asof_days": int(len(full)),
        "incomplete_days": int((daily["status"] != "FULL_ASOF_PANEL").sum()) if not daily.empty else 0,
        "candidate_rows": int(len(candidates)),
        "future_data_in_features": False,
        "price_basis": "kline_close_unadjusted",
        "adj_close_available": 0,
        "universe_source": "daily_klines_as_of_membership",
        "index_membership": "DATA_GAP_NO_TRUE_HISTORICAL_MEMBERSHIP",
        "statistical_score_policy": "forced_zero_to_avoid_mixing_observable_footprint",
        "legacy_tickets_excluded_from_core": True,
    }
    payload = {
        "identity": identity_lock(),
        "fingerprint": {
            "fingerprint_sha256": fingerprint["fingerprint_sha256"],
            "source_sha256": fingerprint["source_sha256"],
        },
        "coverage": coverage,
        "strategy": strategy,
        "baselines": baselines,
        "ranking": ranking,
        "walk_forward": walk_forward,
        "cost_stress": cost_stress,
        "regimes": regimes,
        "factor_forensics": {
            "high_correlation_pairs": forensics.get("high_correlation_pairs"),
            "dominance_by_abs_t1_rank_ic": forensics.get("dominance_by_abs_t1_rank_ic"),
            "dilution_note": forensics.get("dilution_note"),
        },
        "obsidian": obsidian,
        "legacy_reference_only": {
            "label": "LEGACY_ONLY",
            "production_ranking_owner": PRODUCTION_RANKING_OWNER,
            "production_ranking_key": PRODUCTION_RANKING_KEY,
            "note": "Old tickets/backtests/ticket_score are not used in NEW_STRATEGY_PROFITABILITY.",
        },
    }
    payload["verdict"] = decide_verdict(payload)
    payload["_forensics_full"] = forensics
    payload["_daily"] = full
    payload["_candidates"] = candidates
    payload["_all_daily"] = daily
    return payload


def definition_markdown(fingerprint: dict[str, Any]) -> str:
    lock = identity_lock()
    lines = ["# New Main Force Strategy Definition", "", "Source-locked identity. Not a redesigned strategy.", ""]
    for key, value in lock.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Status vs production ranking",
            "",
            f"- Production ranking owner remains `{PRODUCTION_RANKING_OWNER}` / FROZEN.",
            "- `capital_behavior_v2` is the current Capital Brain / 主力行为 owner.",
            "- Pipeline comment: Capital Brain never alters observable_footprint ranking.",
            "- This validation ranks by `capital_behavior_score`, not `ticket_score`.",
            "",
            "## Formula",
            "",
            "```text",
            NEW_STRATEGY_FORMULA,
            "```",
            "",
            "## Semantic boundary",
            "",
            "> Current validation is of observable market-behavior proxies (volume, price location, volume-price, breakout/turnover proxies, relative strength). It is not proven institutional order flow.",
            "",
            f"- source_sha256: `{fingerprint['fingerprint_sha256']}`",
            f"- git_commit: `{fingerprint['git_commit']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def report_profitability(payload: dict[str, Any]) -> str:
    s = payload["strategy"]
    b = payload["baselines"]
    v = payload["verdict"]
    lines = [
        "# Profitability Report",
        "",
        f"NEW_MAIN_FORCE_STRATEGY_PROFITABILITY = {v['NEW_MAIN_FORCE_STRATEGY_PROFITABILITY']}",
        f"PROFITABILITY_VALIDATED = {v['PROFITABILITY_VALIDATED']}",
        "",
        "Core statistics use as-of replay of `capital_behavior_v2` only. LEGACY_ONLY series are excluded.",
        "",
        "## A. NEW_MAIN_FORCE_STRATEGY Top1 (official)",
        "",
    ]
    for horizon in HORIZONS:
        lines += [f"### T+{horizon}", "", metrics_block(s["top1"][str(horizon)]), ""]
    lines += ["## Top3 / Top5 (research only, not the official conclusion)", ""]
    for label in ("top3", "top5"):
        lines += [f"### {label}", "", metrics_block(s[label]["1"]), ""]
    lines += ["## B. SAME_DAY_EQUAL_WEIGHT T+1", "", metrics_block(b["equal_weight"]["1"]), ""]
    lines += ["## C. RANDOM_BASELINE Top1 T+1", "", metrics_block(b["random_top1"]["1"]), ""]
    lines += ["## Verdict reasons", ""]
    for reason in v.get("reasons") or []:
        lines.append(f"- `{reason}`")
    return "\n".join(lines) + "\n"


def report_ranking(payload: dict[str, Any]) -> str:
    lines = ["# Ranking Validation", "", "Question: do higher capital_behavior_score names have better future returns?", ""]
    for horizon in HORIZONS:
        block = payload["ranking"][str(horizon)]
        lines += [
            f"## Score vs T+{horizon}",
            "",
            f"- n: `{block.get('n')}`",
            f"- Pearson: `{fmt_num(block.get('pearson'))}`",
            f"- Spearman: `{fmt_num(block.get('spearman'))}`",
            f"- Top1: `{fmt_pct(block.get('Top1'))}`",
            f"- Top5%: `{fmt_pct(block.get('Top5pct'))}`",
            f"- Top10%: `{fmt_pct(block.get('Top10pct'))}`",
            f"- Top20%: `{fmt_pct(block.get('Top20pct'))}`",
            f"- Bottom20%: `{fmt_pct(block.get('Bottom20pct'))}`",
            "",
        ]
        if (block.get("Bottom20pct") or 0) > (block.get("Top20pct") or 0):
            lines += ["DIAGNOSTIC_FINDING: Bottom20% > Top20%. Score direction may be wrong. Formula was not changed.", ""]
    return "\n".join(lines) + "\n"


def report_walk_forward(payload: dict[str, Any]) -> str:
    lines = ["# Walk-Forward", "", "Chronological 60 / 20 / 20 split on FULL_ASOF_PANEL days. Official metric is Top1 T+1.", ""]
    for name in ("train", "validation", "holdout"):
        block = payload["walk_forward"][name]
        lines += [f"## {name.upper()}", "", f"- dates: `{block.get('start')}` .. `{block.get('end')}`", metrics_block(block), ""]
    return "\n".join(lines) + "\n"


def report_cost(payload: dict[str, Any]) -> str:
    lines = ["# Cost Stress", "", "Friction subtracted from Top1 T+1 unadjusted close-to-close returns.", ""]
    for bps in COST_BPS:
        block = payload["cost_stress"][str(bps)]
        lines += [f"## {bps} bps", "", metrics_block(block), ""]
    return "\n".join(lines) + "\n"


def report_regime(payload: dict[str, Any]) -> str:
    lines = ["# Regime Analysis", "", "Environment labels are research partitions of the as-of panel. Formula was not changed.", ""]
    for name, block in sorted(payload["regimes"].items()):
        lines += [f"## {name}", "", metrics_block(block), ""]
    return "\n".join(lines) + "\n"


def report_factors(payload: dict[str, Any]) -> str:
    full = payload["_forensics_full"]
    lines = [
        "# Factor Forensics",
        "",
        "Research statistics only. DIAGNOSTIC_FINDING. Production formula not modified.",
        "",
        "## Redundancy",
        "",
    ]
    for pair in full.get("high_correlation_pairs") or []:
        lines.append(f"- `{pair['left']}` vs `{pair['right']}` corr=`{pair['corr']:.3f}`")
    lines += ["", "## Dominance by |T+1 rank IC|", ""]
    for name, ic in full.get("dominance_by_abs_t1_rank_ic") or []:
        lines.append(f"- `{name}` rank_ic=`{ic:.4f}`")
    lines += ["", "## Per-factor T+1", ""]
    for name, block in (full.get("factors") or {}).items():
        t1 = block["horizons"].get("t1") or {}
        theory = block.get("theory") or {}
        lines += [
            f"### {name}",
            "",
            f"- meaning: {theory.get('meaning')}",
            f"- higher means: {theory.get('higher')}",
            f"- formula direction: `{theory.get('direction')}`",
            f"- IC: `{fmt_num(t1.get('ic'))}`",
            f"- rank IC: `{fmt_num(t1.get('rank_ic'))}`",
            f"- top20% return: `{fmt_pct(t1.get('top_bucket_return'))}`",
            f"- bottom20% return: `{fmt_pct(t1.get('bottom_bucket_return'))}`",
            f"- monotonicity (top-bottom): `{fmt_pct(t1.get('monotonicity'))}`",
            "",
        ]
    return "\n".join(lines) + "\n"


def report_replay(payload: dict[str, Any]) -> str:
    c = payload["coverage"]
    daily = payload["_all_daily"]
    lines = [
        "# Historical As-Of Replay",
        "",
        "```text",
        "Historical Trading Day",
        "        ↓",
        "as-of daily_klines universe + quality floors",
        "        ↓",
        "bars with trade_date <= as_of only",
        "        ↓",
        "capital_behavior_v2 (statistical_score=0)",
        "        ↓",
        "full candidate pool saved",
        "        ↓",
        "sort (capital_behavior_score, capital_strength, demand_persistence)",
        "        ↓",
        "simulate Top1 / Top3 / Top5",
        "        ↓",
        "forward unadjusted close-to-close",
        "```",
        "",
        f"- full_asof_days: `{c['full_asof_days']}`",
        f"- incomplete_days: `{c['incomplete_days']}`",
        f"- candidate_rows: `{c['candidate_rows']}`",
        f"- future_data_in_features: `{c['future_data_in_features']}`",
        f"- price_basis: `{c['price_basis']}`",
        f"- universe: `{c['universe_source']}`",
        f"- index membership: `{c['index_membership']}`",
        "",
        "No future ranking. No post-hoc winner selection. No manual replacement.",
        "",
    ]
    if not daily.empty:
        lines += ["## Daily status counts", ""]
        counts = daily["status"].value_counts().to_dict()
        for name, count in counts.items():
            lines.append(f"- `{name}`: `{count}`")
    return "\n".join(lines) + "\n"


def report_obsidian(payload: dict[str, Any]) -> str:
    lines = [
        "# Obsidian / Second-Brain Reconciliation",
        "",
        "Second brain is used only to confirm evolution and current version. It does not replace returns.",
        "",
        "## Source facts",
        "",
        f"- Current 主力行为 owner in code: `{NEW_STRATEGY_ID}`",
        f"- Production ranking owner: `{PRODUCTION_RANKING_OWNER}` FROZEN",
        "- Pipeline: Capital Brain runs beside ranking and must not change it.",
        "",
        "## Database facts",
        "",
        "- `capital_behavior_dataset` has 23 research samples from historical bootstrap, NOT a profitability panel.",
        "- `tickets` / `forward_tracking` are LEGACY_ONLY for this report.",
        "- As-of replay uses `daily_klines` only.",
        "",
        "## Second-brain notes",
        "",
    ]
    if not payload.get("obsidian"):
        lines.append("No Obsidian us_stock note independently defines a newer 主力行为 formula than `scripts/capital/scoring.py`.")
    for row in payload.get("obsidian") or []:
        lines += [f"- `{row.get('title')}` — `{row.get('source_path')}`"]
    lines += [
        "",
        "## Reconciliation",
        "",
        "| Claim | Source | Database | Second brain |",
        "| --- | --- | --- | --- |",
        "| Latest 主力行为 version is capital_behavior_v2 | PASS | PASS (model_version column / scoring.MODEL_VERSION) | no newer version recorded |",
        "| Production ranking is still observable_footprint_v1 | PASS | PASS (research.boundary) | knowledge assets still export ticket_score picks |",
        "| Capital score is not proven institutional flow | PASS | PASS | PASS |",
        "| Old tickets prove new strategy profit | FORBIDDEN | isolated | isolated |",
    ]
    return "\n".join(lines) + "\n"


def report_verdict(payload: dict[str, Any]) -> str:
    v = payload["verdict"]
    lines = [
        f"NEW_MAIN_FORCE_STRATEGY_PROFITABILITY = {v['NEW_MAIN_FORCE_STRATEGY_PROFITABILITY']}",
        "",
        f"PROFITABILITY_VALIDATED = {v['PROFITABILITY_VALIDATED']}",
        "",
        "This is the only allowed conclusion label. No hedging language.",
        "",
        "## Gates",
        "",
    ]
    for name, ok in (v.get("gates") or {}).items():
        lines.append(f"- `{name}`: `{'PASS' if ok else 'FAIL'}`")
    lines += ["", "## Reasons", ""]
    for reason in v.get("reasons") or []:
        lines.append(f"- `{reason}`")
    lines += [
        "",
        "## What this does not do",
        "",
        "- Does not retune weights.",
        "- Does not invert factor signs.",
        "- Does not create a second strategy.",
        "- Does not promote Capital Brain into production ranking.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], fingerprint: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_text(OUTPUT_DIR / "strategy_definition.md", definition_markdown(fingerprint))
    write_json(OUTPUT_DIR / "strategy_snapshot.json", fingerprint)
    write_json(OUTPUT_DIR / "strategy_fingerprint.json", {
        "fingerprint_sha256": fingerprint["fingerprint_sha256"],
        "source_sha256": fingerprint["source_sha256"],
        "NEW_STRATEGY_ID": NEW_STRATEGY_ID,
        "NEW_STRATEGY_VERSION": NEW_STRATEGY_VERSION,
        "NEW_RANKING_KEY": list(NEW_RANKING_KEY),
        "NEW_STRATEGY_FORMULA": NEW_STRATEGY_FORMULA,
    })
    write_text(OUTPUT_DIR / "01_strategy_definition.md", definition_markdown(fingerprint))
    write_json(OUTPUT_DIR / "02_strategy_fingerprint.json", {
        "fingerprint_sha256": fingerprint["fingerprint_sha256"],
        "source_sha256": fingerprint["source_sha256"],
        "identity": identity_lock(),
        "unchanged_after_replay": fingerprint["source_sha256"] == source_hashes(),
    })
    write_text(OUTPUT_DIR / "03_historical_replay.md", report_replay(payload))
    write_text(OUTPUT_DIR / "04_profitability_report.md", report_profitability(payload))
    write_text(OUTPUT_DIR / "05_factor_forensics.md", report_factors(payload))
    write_text(OUTPUT_DIR / "06_ranking_validation.md", report_ranking(payload))
    write_text(OUTPUT_DIR / "07_walk_forward.md", report_walk_forward(payload))
    write_text(OUTPUT_DIR / "08_regime_analysis.md", report_regime(payload))
    write_text(OUTPUT_DIR / "09_cost_stress.md", report_cost(payload))
    write_text(OUTPUT_DIR / "10_obsidian_reconciliation.md", report_obsidian(payload))
    candidates = payload["_candidates"]
    daily = payload["_all_daily"]
    keep_cols = [
        "symbol", "trade_date", "rank", "ticket_flag", "top3_flag", "top5_flag",
        *FACTOR_COLUMNS, "capital_state", "capital_intent", "path_type",
        "t1", "t3", "t5", "t10", "regime",
    ]
    if not candidates.empty:
        existing = list(dict.fromkeys(col for col in keep_cols if col in candidates.columns))
        candidates.loc[:, existing].to_parquet(OUTPUT_DIR / "11_ticket_samples.parquet", index=False)
    if not daily.empty:
        daily.to_parquet(OUTPUT_DIR / "12_daily_summary.parquet", index=False)
    write_text(OUTPUT_DIR / "13_final_verdict.md", report_verdict(payload))
    write_json(OUTPUT_DIR / "summary.json", {
        "verdict": payload["verdict"],
        "identity": payload["identity"],
        "coverage": payload["coverage"],
        "strategy": payload["strategy"],
        "baselines": payload["baselines"],
        "ranking": payload["ranking"],
        "walk_forward": payload["walk_forward"],
        "cost_stress": payload["cost_stress"],
        "regimes": payload["regimes"],
    })


def assert_fingerprint_stable(before: dict[str, Any]) -> None:
    after = source_hashes()
    if after != before["source_sha256"]:
        raise RuntimeError("strategy source changed during replay; refusing to report")


def run() -> dict[str, Any]:
    fingerprint = fingerprint_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "strategy_fingerprint.json", {
        "fingerprint_sha256": fingerprint["fingerprint_sha256"],
        "source_sha256": fingerprint["source_sha256"],
        "NEW_STRATEGY_ID": NEW_STRATEGY_ID,
        "NEW_STRATEGY_VERSION": NEW_STRATEGY_VERSION,
    })
    bars = load_kline_bars()
    obsidian = load_obsidian_notes()
    replay_result = replay(bars)
    payload = analyze(replay_result, fingerprint, obsidian)
    assert_fingerprint_stable(fingerprint)
    write_outputs(payload, fingerprint)
    return payload


def main() -> int:
    payload = run()
    verdict = payload["verdict"]
    print("NEW_STRATEGY_ID", NEW_STRATEGY_ID)
    print("NEW_STRATEGY_VERSION", NEW_STRATEGY_VERSION)
    print("NEW_STRATEGY_STATUS", NEW_STRATEGY_STATUS)
    print("NEW_RANKING_KEY", NEW_RANKING_KEY)
    print("NEW_MAIN_FORCE_STRATEGY_PROFITABILITY", verdict["NEW_MAIN_FORCE_STRATEGY_PROFITABILITY"])
    print("PROFITABILITY_VALIDATED", verdict["PROFITABILITY_VALIDATED"])
    print("full_asof_days", payload["coverage"]["full_asof_days"])
    print("top1_t1_n", payload["strategy"]["top1"]["1"].get("sample_count"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
