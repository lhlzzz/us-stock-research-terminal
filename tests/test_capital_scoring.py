from capital import build_capital_assessment
from capital_test_support import ohlcv


def test_parallel_scores_are_bounded_and_not_production_ready():
    assessment = build_capital_assessment(ohlcv(), statistical_score=0.8)
    assert assessment["validation_status"] == "UNVALIDATED_NO_FIXED_CHAIN"
    assert all(0 <= assessment["scores"][key] <= 1 for key in ("statistical_score", "capital_score", "combined_score", "capital_behavior_score"))


def test_capital_behavior_score_is_independent_of_statistical_score():
    weak = build_capital_assessment(ohlcv(), statistical_score=0.1)
    strong = build_capital_assessment(ohlcv(), statistical_score=0.9)
    assert weak["scores"]["capital_behavior_score"] == strong["scores"]["capital_behavior_score"]
    assert weak["scores"]["capital_score"] == weak["scores"]["capital_behavior_score"]
    assert strong["scores"]["combined_score"] != strong["scores"]["capital_behavior_score"]
    assert strong["scores"]["combined_score"] > weak["scores"]["combined_score"]
