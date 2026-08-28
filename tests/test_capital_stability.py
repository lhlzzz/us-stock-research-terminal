from capital.feature_stability import feature_stability


def test_feature_stability_reports_multiple_diagnostics_without_positive_ic_gate():
    rows = [{"feature": index / 10, "return_3d": (-1 if index % 2 else 1) * 0.01} for index in range(30)]
    result = feature_stability(rows, features=("feature",), min_samples=10)
    assert result["status"] == "RESEARCH_ONLY"
    assert "ic" in result["features"]["feature"]
    assert "rank_ic" in result["features"]["feature"]
    assert "mutual_information" in result["features"]["feature"]
    assert "bucket_monotonicity" in result["features"]["feature"]
