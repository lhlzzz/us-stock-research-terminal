from capital.archetypes import classify_archetype


def test_archetypes_are_observable_and_deterministic():
    sample = {
        "capital_state": "PULLBACK_ABSORPTION", "absorption": 0.9,
        "absorption_persistence": 0.8, "damage_efficiency": 0.8,
        "demand_persistence": 0.6, "supply_exhaustion": 0.7,
        "markup": 0.3, "distribution": 0.1, "crowding": 0.1,
        "trap": 0.1, "upward_pressure": 0.6, "downward_pressure": 0.4,
        "control_asymmetry": 0.2,
    }
    first = classify_archetype(sample)
    second = classify_archetype(sample)
    assert first == second
    assert first["semantic"] == "OBSERVABLE_BEHAVIOR_PATTERN"
    assert 0 <= first["score"] <= 1
