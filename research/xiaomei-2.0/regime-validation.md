# Regime Validation

Status: **VALIDATION_GAP**

Research classifier (`scripts/research/regime.py`) is parallel to production `scripts/market_regime.py` (risk_on / active / balanced / risk_off). Production classifier is not replaced.

Research regimes: RISK_ON, RISK_OFF, TRENDING, MEAN_REVERSION, HIGH_VOL, LOW_VOL, EARNINGS_SEASON, POST_EARNINGS.

Per-regime effectiveness fields: factor_effectiveness, capital_behavior_effectiveness, setup_effectiveness. Assumption rejected: same factor = all market regimes.

Earnings regimes: PRE_EARNINGS, EARNINGS_DAY, POST_EARNINGS, POST_GUIDANCE. Conclusion must state NORMAL_SETUP or EVENT_SETUP.

Live per-regime sample counts are below MIN_CONDITION_SAMPLES=20. Status remains VALIDATION_GAP.
