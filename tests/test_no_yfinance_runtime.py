from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YFINANCE_TOKENS = [
    "import yfinance",
    "from yfinance",
    "yf.Ticker",
    "yf.download",
]
FORBIDDEN_RUNTIME_TOKENS = [
    "ensure_proxy_env",
    "normalize_yahoo_symbol",
]
YFINANCE_ALLOWED_PATHS = {Path("scripts/historical_replay_baseline.py")}


def test_yfinance_is_limited_to_historical_kline_layer():
    paths = list((ROOT / "scripts").glob("*.py")) + list((ROOT / "skills").rglob("*.md"))
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        for token in YFINANCE_TOKENS:
            if token in text and relative not in YFINANCE_ALLOWED_PATHS:
                offenders.append(f"{relative}: {token}")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            if token in text:
                offenders.append(f"{relative}: {token}")
    assert offenders == []
