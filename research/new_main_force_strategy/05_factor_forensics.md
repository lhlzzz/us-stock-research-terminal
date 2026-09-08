# Factor Forensics

Research statistics only. DIAGNOSTIC_FINDING. Production formula not modified.

## Redundancy

- `upward_pressure` vs `downward_pressure` corr=`-0.996`
- `upward_pressure` vs `demand_persistence` corr=`0.863`
- `upward_pressure` vs `accumulation` corr=`0.822`
- `upward_pressure` vs `markup` corr=`0.955`
- `downward_pressure` vs `demand_persistence` corr=`-0.890`
- `downward_pressure` vs `accumulation` corr=`-0.840`
- `downward_pressure` vs `markup` corr=`-0.936`
- `demand_persistence` vs `accumulation` corr=`0.917`
- `distribution` vs `trap` corr=`0.885`
- `distribution` vs `distribution_probability` corr=`0.928`
- `distribution` vs `trap_probability` corr=`0.922`
- `trap` vs `capital_quality` corr=`-0.870`
- `trap` vs `distribution_probability` corr=`0.936`
- `trap` vs `trap_probability` corr=`0.969`
- `price_damage` vs `absorption_failure` corr=`0.957`
- `damage_efficiency` vs `absorption_failure` corr=`-0.832`
- `capital_quality` vs `distribution_probability` corr=`-0.836`
- `capital_quality` vs `trap_probability` corr=`-0.934`
- `distribution_probability` vs `trap_probability` corr=`0.936`

## Dominance by |T+1 rank IC|

- `distribution_probability` rank_ic=`0.0231`
- `capital_quality` rank_ic=`-0.0205`
- `trap` rank_ic=`0.0197`
- `distribution` rank_ic=`0.0190`
- `trap_probability` rank_ic=`0.0190`
- `crowding` rank_ic=`0.0186`
- `selling_activity` rank_ic=`0.0174`
- `accumulation` rank_ic=`-0.0155`

## Per-factor T+1

### upward_pressure

- meaning: recent upside return/volume/close position
- higher means: more upside pressure
- formula direction: `+`
- IC: `-0.0089`
- rank IC: `-0.0103`
- top20% return: `+0.12%`
- bottom20% return: `+0.18%`
- monotonicity (top-bottom): `-0.06%`

### downward_pressure

- meaning: recent downside return/volume/weak close
- higher means: more downside pressure
- formula direction: `-_as_quality`
- IC: `0.0087`
- rank IC: `0.0106`
- top20% return: `+0.20%`
- bottom20% return: `+0.11%`
- monotonicity (top-bottom): `+0.09%`

### volume_pressure

- meaning: volume vs 20d baseline and persistence
- higher means: more activity
- formula direction: `mixed`
- IC: `0.0066`
- rank IC: `0.0089`
- top20% return: `+0.21%`
- bottom20% return: `+0.04%`
- monotonicity (top-bottom): `+0.16%`

### demand_persistence

- meaning: positive days, 5d return, recovery, RS
- higher means: demand more persistent
- formula direction: `+`
- IC: `-0.0070`
- rank IC: `-0.0125`
- top20% return: `+0.06%`
- bottom20% return: `+0.24%`
- monotonicity (top-bottom): `-0.18%`

### supply_exhaustion

- meaning: failed breakdown, higher low, decaying downside volume
- higher means: supply fading
- formula direction: `+`
- IC: `-0.0024`
- rank IC: `-0.0076`
- top20% return: `+0.04%`
- bottom20% return: `+0.16%`
- monotonicity (top-bottom): `-0.12%`

### absorption

- meaning: selling activity absorbed with low damage
- higher means: better absorption proxy
- formula direction: `+`
- IC: `0.0026`
- rank IC: `0.0028`
- top20% return: `+0.05%`
- bottom20% return: `+0.13%`
- monotonicity (top-bottom): `-0.08%`

### accumulation

- meaning: absorption + supply exhaustion + RS
- higher means: more accumulation-like tape
- formula direction: `+`
- IC: `-0.0077`
- rank IC: `-0.0155`
- top20% return: `+0.08%`
- bottom20% return: `+0.17%`
- monotonicity (top-bottom): `-0.10%`

### markup

- meaning: upward pressure + demand + volume + RS
- higher means: more markup-like tape
- formula direction: `+`
- IC: `-0.0064`
- rank IC: `-0.0105`
- top20% return: `+0.14%`
- bottom20% return: `+0.15%`
- monotonicity (top-bottom): `-0.02%`

### distribution

- meaning: high activity with poor price progress
- higher means: more distribution-like tape
- formula direction: `-`
- IC: `0.0195`
- rank IC: `0.0190`
- top20% return: `+0.26%`
- bottom20% return: `+0.00%`
- monotonicity (top-bottom): `+0.25%`

### crowding

- meaning: late extension, volume spike, concentration
- higher means: more crowded tape
- formula direction: `-`
- IC: `0.0190`
- rank IC: `0.0186`
- top20% return: `+0.21%`
- bottom20% return: `-0.00%`
- monotonicity (top-bottom): `+0.21%`

### trap

- meaning: distribution + weak close after volume
- higher means: more trap-like tape
- formula direction: `-`
- IC: `0.0146`
- rank IC: `0.0197`
- top20% return: `+0.24%`
- bottom20% return: `-0.00%`
- monotonicity (top-bottom): `+0.24%`

### selling_activity

- meaning: down-volume share and downside returns
- higher means: more selling activity
- formula direction: `mixed`
- IC: `0.0139`
- rank IC: `0.0174`
- top20% return: `+0.18%`
- bottom20% return: `+0.03%`
- monotonicity (top-bottom): `+0.15%`

### price_damage

- meaning: downside return vs volatility and support
- higher means: more damage
- formula direction: `-`
- IC: `0.0102`
- rank IC: `0.0128`
- top20% return: `+0.24%`
- bottom20% return: `+0.09%`
- monotonicity (top-bottom): `+0.15%`

### damage_efficiency

- meaning: 1 - actual_damage/expected_damage
- higher means: less damage than expected
- formula direction: `+`
- IC: `-0.0026`
- rank IC: `-0.0053`
- top20% return: `+0.08%`
- bottom20% return: `+0.18%`
- monotonicity (top-bottom): `-0.10%`

### absorption_failure

- meaning: selling plus damage minus efficiency
- higher means: absorption failing
- formula direction: `-`
- IC: `0.0108`
- rank IC: `0.0147`
- top20% return: `+0.25%`
- bottom20% return: `+0.06%`
- monotonicity (top-bottom): `+0.19%`

### price_response_efficiency

- meaning: directional response per activity
- higher means: price responds more to activity
- formula direction: `+`
- IC: `-0.0008`
- rank IC: `-0.0024`
- top20% return: `+0.11%`
- bottom20% return: `+0.10%`
- monotonicity (top-bottom): `+0.01%`

### control_asymmetry

- meaning: upside minus downside control
- higher means: long control advantage
- formula direction: `+_abs_in_score`
- IC: `-0.0070`
- rank IC: `-0.0070`
- top20% return: `+0.04%`
- bottom20% return: `+0.16%`
- monotonicity (top-bottom): `-0.11%`

### capital_strength

- meaning: weighted pressure/persistence/absorption/control
- higher means: stronger observable pressure
- formula direction: `+`
- IC: `0.0016`
- rank IC: `-0.0043`
- top20% return: `+0.11%`
- bottom20% return: `+0.09%`
- monotonicity (top-bottom): `+0.02%`

### capital_quality

- meaning: persistence/absorption minus distribution/trap
- higher means: healthier tape quality
- formula direction: `+`
- IC: `-0.0154`
- rank IC: `-0.0205`
- top20% return: `-0.01%`
- bottom20% return: `+0.23%`
- monotonicity (top-bottom): `-0.25%`

### distribution_probability

- meaning: distribution + crowding + absorption failure
- higher means: higher distribution risk proxy
- formula direction: `-`
- IC: `0.0205`
- rank IC: `0.0231`
- top20% return: `+0.26%`
- bottom20% return: `-0.02%`
- monotonicity (top-bottom): `+0.28%`

### trap_probability

- meaning: trap + distribution + weak confidence
- higher means: higher trap risk proxy
- formula direction: `-`
- IC: `0.0159`
- rank IC: `0.0190`
- top20% return: `+0.23%`
- bottom20% return: `-0.00%`
- monotonicity (top-bottom): `+0.23%`

### capital_behavior_score

- meaning: official capital_behavior_v2 ranking score
- higher means: ranked better by current formula
- formula direction: `+`
- IC: `-0.0093`
- rank IC: `-0.0123`
- top20% return: `+0.07%`
- bottom20% return: `+0.16%`
- monotonicity (top-bottom): `-0.10%`

