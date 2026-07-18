#!/usr/bin/env python3
"""Social Sentiment Analyzer: 从社交平台提取情绪信号。

数据源优先级：
1. last30days (Reddit/YouTube/HN/Polymarket)
2. Finviz social sentiment (备用)
3. 默认值 0.3

输出：0-1 情绪评分，用于 factor_snapshots 和 scoring
"""
import sys
import json
import os
import re
from pathlib import Path
from datetime import date, timedelta
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LAST30DAYS_SCRIPT = Path("/root/.agents/skills/last30days/scripts/last30days.py")
LAST30DAYS_PYTHON = Path("/root/.local/share/hermes-tools/last30days-py312/bin/python")
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "social-sentiment-cache"

# Cache TTL: 7 days
CACHE_TTL_DAYS = 7


def analyze_social_sentiment(symbol: str, company_name: str = "") -> dict:
    """分析单个股票的社交情绪。"""
    cache_key = f"{symbol}_{date.today()}.json"
    cache_path = CACHE_DIR / cache_key

    # Check cache (with TTL)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            cache_date = cached.get("_cache_date")
            if cache_date:
                cache_dt = date.fromisoformat(cache_date)
                if (date.today() - cache_dt).days <= CACHE_TTL_DAYS:
                    return cached
        except Exception:
            pass

    # Try sources in order
    result = None

    # 1. Try last30days (fast mode)
    result = _fetch_last30days(symbol, company_name)
    if result and result.get("source") == "last30days":
        result["_cache_date"] = date.today().isoformat()
        _save_cache(cache_path, result)
        return result

    # 2. Try finviz fallback
    result = _fetch_finviz_sentiment(symbol)
    if result and result.get("source") == "finviz":
        result["_cache_date"] = date.today().isoformat()
        _save_cache(cache_path, result)
        return result

    # 3. Default
    result = _default_sentiment()
    result["_cache_date"] = date.today().isoformat()
    _save_cache(cache_path, result)
    return result


def _save_cache(cache_path: Path, result: dict):
    """Save to cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, ensure_ascii=False))


def _fetch_last30days(symbol: str, company_name: str) -> dict | None:
    """通过 last30days 获取社交数据（快速模式）。"""
    if not LAST30DAYS_PYTHON.exists() or not LAST30DAYS_SCRIPT.exists():
        return None

    # Only try 1 topic with shorter timeout
    topic = f"{symbol} stock"
    try:
        import subprocess
        result = subprocess.run(
            [str(LAST30DAYS_PYTHON), str(LAST30DAYS_SCRIPT),
             topic, "--quick", "--days", "7", "--emit", "json"],
            capture_output=True, text=True, timeout=15,  # 15s timeout
        )
        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        start = output.find("{")
        if start == -1:
            return None

        payload, _ = json.JSONDecoder().raw_decode(output[start:])
        ranked = payload.get("ranked_candidates", [])
        if ranked:
            return _compute_sentiment(payload)

    except (subprocess.TimeoutExpired, Exception):
        pass

    return None


def _fetch_finviz_sentiment(symbol: str) -> dict | None:
    """从 Finviz 获取社交情绪（备用源）。"""
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://finviz.com/quote.ashx?t={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract analyst recommendation
        recommendation = 0.5
        buzz = 0.0

        # Look for recommendation data in the page
        text = soup.get_text()

        # Try to find "Strong Buy", "Buy", "Hold", "Sell" counts
        buy_match = re.search(r"Buy.*?(\d+)", text)
        sell_match = re.search(r"Sell.*?(\d+)", text)
        hold_match = re.search(r"Hold.*?(\d+)", text)

        if buy_match and sell_match:
            buys = int(buy_match.group(1))
            sells = int(sell_match.group(1))
            holds = int(hold_match.group(1)) if hold_match else 0
            total = buys + sells + holds
            if total > 0:
                recommendation = (buys * 1.0 + holds * 0.5 + sells * 0.0) / total
                buzz = min(1.0, total / 30.0)  # Normalize buzz

        # Look for social media mentions
        social_match = re.search(r"Social.*?(\d+)", text)
        if social_match:
            mentions = int(social_match.group(1))
            buzz = min(1.0, mentions / 100.0)

        composite = recommendation * 0.6 + buzz * 0.4

        return {
            "sentiment_score": round(recommendation, 4),
            "buzz_score": round(buzz, 4),
            "composite_score": round(composite, 4),
            "total_posts": 0,
            "positive_signals": 0,
            "negative_signals": 0,
            "source": "finviz",
        }

    except Exception:
        return None


def _compute_sentiment(payload: dict) -> dict:
    """从 last30days 输出计算情绪评分。"""
    ranked = payload.get("ranked_candidates", [])
    clusters = payload.get("clusters", [])
    total_posts = len(ranked)

    positive_signals = 0
    negative_signals = 0
    total_score = 0.0

    for item in ranked:
        title = (item.get("title") or "").lower()
        snippet = (item.get("snippet") or "").lower()
        text = f"{title} {snippet}"

        pos_words = ["surge", "rally", "beat", "upgrade", "buy", "bullish", "growth", "strong", "record", "breakout", "profit", "gain", "rise", "jump", "soar"]
        neg_words = ["crash", "drop", "miss", "downgrade", "sell", "bearish", "loss", "weak", "decline", "plunge", "fear", "risk", "warning", "cut", "fall"]

        pos_count = sum(1 for w in pos_words if w in text)
        neg_count = sum(1 for w in neg_words if w in text)

        quality = item.get("source_quality", 0.5)
        weight = 0.5 + quality * 0.5

        if pos_count > neg_count:
            positive_signals += 1
            total_score += 0.1 * weight
        elif neg_count > pos_count:
            negative_signals += 1
            total_score -= 0.1 * weight

    cluster_bonus = min(0.2, len(clusters) * 0.05)

    if total_posts > 0:
        sentiment_score = max(0.0, min(1.0, 0.5 + total_score + cluster_bonus))
        buzz_score = min(1.0, total_posts / 8.0)
    else:
        sentiment_score = 0.5
        buzz_score = 0.0

    composite = sentiment_score * 0.6 + buzz_score * 0.4

    return {
        "sentiment_score": round(sentiment_score, 4),
        "buzz_score": round(buzz_score, 4),
        "composite_score": round(composite, 4),
        "total_posts": total_posts,
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "clusters": len(clusters),
        "source": "last30days",
    }


def _default_sentiment() -> dict:
    return {
        "sentiment_score": 0.5,
        "buzz_score": 0.0,
        "composite_score": 0.3,
        "total_posts": 0,
        "positive_signals": 0,
        "negative_signals": 0,
        "source": "default",
    }


def batch_analyze(symbols: list[dict]) -> dict[str, dict]:
    """批量分析社交情绪。优先使用 Scrapy 批量采集。"""
    symbol_list = [item.get("symbol", "") for item in symbols if item.get("symbol")]

    # Try Scrapy batch first (much faster)
    try:
        from social_scraper import batch_analyze_sentiment
        return batch_analyze_sentiment(symbol_list)
    except Exception:
        pass

    # Fallback to individual analysis
    results = {}
    for item in symbols:
        sym = item.get("symbol", "")
        name = item.get("name", "")
        if sym:
            results[sym] = analyze_social_sentiment(sym, name)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Social sentiment analyzer")
    parser.add_argument("--symbol", default="MU")
    parser.add_argument("--name", default="Micron Technology")
    args = parser.parse_args()

    result = analyze_social_sentiment(args.symbol, args.name)
    print(json.dumps(result, indent=2, ensure_ascii=False))
