from capital.evaluation import calibration_error, classification_metrics, economic_metrics, multiclass_brier, multiclass_log_loss


def test_evaluation_returns_not_ready_without_minimum_samples():
    assert classification_metrics(["A"], ["A"], min_samples=2)["status"] == "NOT_READY"
    assert multiclass_brier([{"A": 1.0}], ["A"], min_samples=2)["status"] == "NOT_READY"
    assert multiclass_log_loss([{"A": 1.0}], ["A"], min_samples=2)["status"] == "NOT_READY"
    assert calibration_error([{"A": 1.0}], ["A"], min_samples=2)["status"] == "NOT_READY"


def test_evaluation_exposes_classification_calibration_and_economic_metrics():
    actual = ["A", "A", "B", "B"]
    predicted = ["A", "B", "B", "B"]
    probabilities = [{"A": 0.8, "B": 0.2}, {"A": 0.6, "B": 0.4}, {"A": 0.2, "B": 0.8}, {"A": 0.1, "B": 0.9}]
    metrics = classification_metrics(actual, predicted)
    assert metrics["accuracy"] == 0.75
    assert "macro_f1" in metrics and "confusion_matrix" in metrics
    assert multiclass_brier(probabilities, actual)["status"] == "RESEARCH_ONLY"
    assert multiclass_log_loss(probabilities, actual)["status"] == "RESEARCH_ONLY"
    assert calibration_error(probabilities, actual)["status"] == "RESEARCH_ONLY"
    economic = economic_metrics([0.1, -0.05, 0.02], mfe=(0.12, 0.03), mae=(-0.04, -0.02))
    assert economic["profit_factor"] > 1
    assert economic["mfe"] == 0.075
    assert economic["mae"] == -0.03
