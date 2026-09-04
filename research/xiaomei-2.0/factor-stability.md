# Factor Stability

Status: **MODEL_GAP** / **VALIDATION_GAP**

Layer: `scripts/research/stability.py`. Production `weight_optimizer.py` still requires VALIDATED_FOR_WEIGHT_UPDATE and now consults `weight_change_guard` before writing.

Outputs per factor: current_ic, rolling_30d_ic, rolling_60d_ic, rolling_120d_ic, walk_forward_ic, regime_ic, sector_ic, sign_stability, coverage, factor_status.

factor_status: STABLE / DEGRADING / UNSTABLE / REVERSED / INSUFFICIENT_DATA.

weight_change_guard:

- max per-period change 0.10
- confirmation_periods = 2
- min samples = 20
- min trading days = 10
- sign stability
- default action without evidence: KEEP_PREVIOUS_WEIGHT

High IC is not a permanent weight. `run_weekly_optimization` does not write production weights when the guard keeps the previous vector.

Live versioned completed IC sample is still below the production gate (UNVALIDATED_NO_FIXED_CHAIN). Gates were not lowered.
