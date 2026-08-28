from capital.calibration import evaluate_calibration


def test_calibration_does_not_fabricate_zero_sample_precision():
    result = evaluate_calibration([], [])
    assert result["status"] == "UNAVAILABLE_NO_FIXED_CHAIN"
    assert result["brier_score"]["value"] is None
    assert result["log_loss"]["value"] is None
