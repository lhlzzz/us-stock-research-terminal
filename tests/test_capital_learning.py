from capital.learning import empirical_distribution, fit_empirical_baseline, hybrid_probability, predict_empirical


def _samples(count=30):
    return [
        {
            "eligibility_reason": "VALID",
            "capital_state": "ACCUMULATION" if index % 2 else "ACTIVE_MARKUP",
            "future_outcome": {
                "state_after_3d": "EARLY_BUILD",
                "transition_after_3d": "ACCUMULATION->EARLY_BUILD",
                "intent_after_3d": "BUILD",
                "path_after_3d": "UP_CONTINUATION",
            },
        }
        for index in range(count)
    ]


def test_empirical_distribution_is_gated_and_deterministic():
    not_ready = empirical_distribution(_samples(2), condition_keys=("capital_state",), outcome_key="future_outcome.state_after_3d")
    split_ready_not = empirical_distribution(_samples(30), condition_keys=("capital_state",), outcome_key="future_outcome.state_after_3d")
    ready = empirical_distribution(_samples(40), condition_keys=("capital_state",), outcome_key="future_outcome.state_after_3d")
    assert not_ready["status"] == "NOT_READY"
    assert split_ready_not["status"] == "NOT_READY"
    assert split_ready_not["min_condition_samples"] == 20
    assert ready["status"] == "RESEARCH_ONLY"
    assert ready["probabilities"]["ACCUMULATION"] == {"EARLY_BUILD": 1.0}


def test_baseline_prediction_and_hybrid_keep_rule_probability_visible():
    model = fit_empirical_baseline(_samples(), min_samples=5)
    prediction = predict_empirical(model, {"capital_state": "ACCUMULATION"}, model_name="state_model")
    assert prediction == {"EARLY_BUILD": 1.0}
    hybrid = hybrid_probability({"EARLY_BUILD": 0.2, "NEUTRAL": 0.8}, prediction)
    assert hybrid["status"] == "RESEARCH_ONLY"
    assert hybrid["rule_probability"] == {"EARLY_BUILD": 0.2, "NEUTRAL": 0.8}
    assert abs(sum(hybrid["hybrid_probability"].values()) - 1.0) < 1e-6


def test_baseline_filters_ineligible_samples():
    model = fit_empirical_baseline(_samples(30) + [{"eligibility_reason": "INSUFFICIENT_FORWARD_DATA", "capital_state": "ACCUMULATION"}], min_samples=5)
    assert model["sample_count"] == 30


def test_baseline_uses_only_requested_temporal_partition_when_present():
    rows = _samples(6)
    rows[:3] = [{**row, "dataset_split": "TRAIN"} for row in rows[:3]]
    rows[3:] = [{**row, "dataset_split": "TEST"} for row in rows[3:]]
    model = fit_empirical_baseline(rows, min_samples=1, split="TRAIN")
    assert model["fit_split"] == "TRAIN"
    assert model["sample_count"] == 3


def test_baseline_is_not_ready_until_all_output_models_have_samples():
    model = fit_empirical_baseline(_samples(), min_samples=5)
    assert model["status"] == "NOT_READY"
