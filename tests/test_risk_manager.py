#!/usr/bin/env python3
"""Tests for risk_manager module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from risk_manager import (
    DEFAULT_RISK_PER_TRADE,
    MAX_CONSECUTIVE_LOSSES,
    RiskState,
    assess_trade_risk,
    build_candidate_risk_record,
    calculate_kelly_fraction,
    calculate_position_size,
    calculate_stop_loss,
    calculate_take_profit,
    calculate_trailing_stop,
    update_risk_state,
)


def test_position_size_basic():
    shares = calculate_position_size(
        account_balance=100_000,
        entry_price=100.0,
        stop_loss_pct=0.02,
        risk_per_trade=0.02,
    )
    assert shares == 1000.0


def test_position_size_zero_price():
    shares = calculate_position_size(100_000, 0.0, 0.02)
    assert shares == 0.0


def test_kelly_basic():
    kelly = calculate_kelly_fraction(0.6, 0.04, 0.02)
    assert kelly > 0.0


def test_kelly_half():
    kelly = calculate_kelly_fraction(0.5, 0.04, 0.02, fraction=0.5)
    assert kelly >= 0.0


def test_stop_loss_fixed():
    sl = calculate_stop_loss(100.0, fixed_pct=0.02)
    assert sl == 98.0


def test_stop_loss_atr():
    sl = calculate_stop_loss(100.0, atr=2.0)
    assert sl == 96.0


def test_take_profit():
    tp = calculate_take_profit(100.0, 98.0, risk_reward_ratio=2.0)
    assert tp == 104.0


def test_trailing_stop_not_activated():
    ts = calculate_trailing_stop(100.0, 101.0, 101.0)
    assert ts is None


def test_trailing_stop_activated():
    ts = calculate_trailing_stop(100.0, 110.0, 110.0, activation_r=1.5, trail_pct=0.1)
    assert ts is not None
    assert ts > 100.0


def test_risk_assessment_allowed():
    state = RiskState()
    assessment = assess_trade_risk(
        symbol="AAPL",
        entry_price=150.0,
        current_price=150.0,
        account_balance=100_000.0,
        risk_state=state,
    )
    assert assessment.allowed is True
    assert assessment.risk_parameters.entry_price == 150.0


def test_risk_assessment_blocked_cooldown():
    state = RiskState(consecutive_losses=3)
    assessment = assess_trade_risk(
        symbol="AAPL",
        entry_price=150.0,
        current_price=150.0,
        account_balance=100_000.0,
        risk_state=state,
    )
    assert assessment.allowed is False
    assert "cooldown" in assessment.block_reason


def test_risk_assessment_blocked_daily_limit():
    state = RiskState(is_daily_limit_hit=True)
    assessment = assess_trade_risk(
        symbol="AAPL",
        entry_price=150.0,
        current_price=150.0,
        account_balance=100_000.0,
        risk_state=state,
    )
    assert assessment.allowed is False
    assert "daily_loss_limit" in assessment.block_reason


def test_update_risk_state_loss():
    state = RiskState()
    state = update_risk_state(state, -500.0, 100_000.0)
    assert state.daily_pnl == -500.0
    assert state.consecutive_losses == 1


def test_update_risk_state_win():
    state = RiskState(consecutive_losses=2)
    state = update_risk_state(state, 1000.0, 100_000.0)
    assert state.consecutive_losses == 0


def test_build_candidate_risk_record():
    record = build_candidate_risk_record(
        symbol="NVDA",
        entry_price=120.0,
        current_price=120.0,
        account_balance=100_000.0,
    )
    assert record["symbol"] == "NVDA"
    assert "risk_allowed" in record
    assert "stop_loss" in record
    assert "take_profit" in record
    assert "kelly_fraction" in record
