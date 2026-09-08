# New Main Force Strategy Definition

Source-locked identity. Not a redesigned strategy.

- `NEW_STRATEGY_ID`: `capital_behavior_v2`
- `NEW_STRATEGY_VERSION`: `capital_behavior_v2`
- `NEW_STRATEGY_STATUS`: `UNVALIDATED_NO_FIXED_CHAIN`
- `NEW_STRATEGY_FORMULA`: `clamp(0.55*capital_strength + 0.25*capital_quality + 0.20*|control_asymmetry| - 0.18*distribution_probability - 0.12*trap_probability)`
- `NEW_STRATEGY_FACTORS`: `upward_pressure,downward_pressure,volume_pressure,demand_persistence,supply_exhaustion,absorption,accumulation,markup,distribution,crowding,trap,selling_activity,price_damage,damage_efficiency,absorption_failure,price_response_efficiency,control_asymmetry,capital_strength,capital_quality,distribution_probability,trap_probability,capital_behavior_score`
- `NEW_STRATEGY_WEIGHTS`: `{"abs_control_asymmetry": 0.2, "capital_quality": 0.25, "capital_strength": 0.55, "capital_strength_components": {"absorption": 0.14, "demand_persistence": 0.16, "direction_pressure": 0.22, "price_response_efficiency": 0.14, "regime_alignment": 0.04, "selling_activity": 0.14, "state_confidence": 0.1, "transition_confidence": 0.1}, "distribution_probability": -0.18, "trap_probability": -0.12}`
- `NEW_RANKING_KEY`: `capital_behavior_score,capital_strength,demand_persistence`
- `NEW_TICKET_RULE`: `Top1 by NEW_RANKING_KEY after quality filter; no capital MIN_SCORE`
- `NEW_UNIVERSE_RULE`: `daily_klines as-of membership; history>=200; close>=5; median dollar volume>=5e6; as_of bar required`
- `NEW_ENTRY_TIME`: `US regular session close complete bar; paper ticket after BJT 04:00`
- `NEW_FORWARD_RULE`: `unadjusted kline close[as_of] -> close[CALENDAR.add_trading_days(as_of,h)]`

## Status vs production ranking

- Production ranking owner remains `observable_footprint_v1` / FROZEN.
- `capital_behavior_v2` is the current Capital Brain / 主力行为 owner.
- Pipeline comment: Capital Brain never alters observable_footprint ranking.
- This validation ranks by `capital_behavior_score`, not `ticket_score`.

## Formula

```text
clamp(0.55*capital_strength + 0.25*capital_quality + 0.20*|control_asymmetry| - 0.18*distribution_probability - 0.12*trap_probability)
```

## Semantic boundary

> Current validation is of observable market-behavior proxies (volume, price location, volume-price, breakout/turnover proxies, relative strength). It is not proven institutional order flow.

- source_sha256: `defbef8be7b2f1dc845f9a04597ab43dae9d6cd5285fb11c6e01952815e50b18`
- git_commit: `c87c4584ec6216b83de1234171b2f1be330549ff`
