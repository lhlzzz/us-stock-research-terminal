from capital import build_capital_assessment
from capital.path import PATHS
from capital_test_support import ohlcv


def test_competing_paths_are_simplexes_for_each_horizon():
    path = build_capital_assessment(ohlcv())["path"]
    for horizon in ("t1", "t3", "t5"):
        distribution = path[f"path_distribution_{horizon}"]
        assert set(distribution) == set(PATHS)
        assert abs(sum(distribution.values()) - 1.0) < 1e-6
        assert all(0 <= value <= 1 for value in distribution.values())
    assert path["path_sequence"]
    assert path["path_invalidation"]
