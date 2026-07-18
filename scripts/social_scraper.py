#!/usr/bin/env python3
"""High-performance social sentiment scraper using Scrapy.

Batch scrapes multiple stocks from finviz in parallel.
Extracts analyst recommendations, institutional ownership, short interest
as proxies for social sentiment.

Usage:
    python3 scripts/social_scraper.py --symbols NVDA TSLA AMD META CRM
"""
import csv
import json
import re
import sys
from pathlib import Path
from datetime import date
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "social-sentiment-cache"


def _parse_percentage(text: str) -> float | None:
    """Parse percentage string like '70.41%' to 0.7041."""
    match = re.search(r"([\d.]+)%", text)
    if match:
        return float(match.group(1)) / 100.0
    return None


def _parse_number(text: str) -> float | None:
    """Parse number string like '1.89' or '299.67M'."""
    text = text.strip().replace(",", "")
    if text.endswith("M"):
        return float(text[:-1]) * 1_000_000
    elif text.endswith("B"):
        return float(text[:-1]) * 1_000_000_000
    elif text.endswith("K"):
        return float(text[:-1]) * 1_000
    try:
        return float(text)
    except ValueError:
        return None


def scrape_finviz_batch(symbols: list[str], max_concurrent: int = 5) -> dict[str, dict]:
    """Batch scrape finviz for multiple symbols using Scrapy.
    
    Extracts: analyst recommendation, insider/inst ownership, short interest,
    performance metrics as sentiment proxies.
    
    Returns dict mapping symbol -> sentiment dict.
    """
    import scrapy
    from scrapy.crawler import CrawlerProcess
    
    results = {}
    
    class FinvizSpider(scrapy.Spider):
        name = "finviz"
        custom_settings = {
            "CONCURRENT_REQUESTS": max_concurrent,
            "DOWNLOAD_DELAY": 0.3,
            "ROBOTSTXT_OBEY": False,
            "LOG_LEVEL": "WARNING",
            "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        def __init__(self, symbols_list):
            self.symbols_list = symbols_list
            self.start_urls = [
                f"https://finviz.com/quote.ashx?t={sym}" for sym in symbols_list
            ]
        
        def parse(self, response):
            symbol = response.url.split("t=")[-1].split("&")[0]
            
            # Extract all snapshot table data
            data = {}
            tables = response.css("table.snapshot-table2")
            for table in tables:
                rows = table.css("tr")
                for row in rows:
                    cells = row.css("td").getall()
                    if len(cells) >= 2:
                        # Clean HTML tags
                        label = re.sub(r"<[^>]+>", "", cells[0]).strip()
                        value = re.sub(r"<[^>]+>", "", cells[1]).strip()
                        data[label] = value
            
            # Extract sentiment proxies
            insider_own = _parse_percentage(data.get("Insider Own", "0%"))
            inst_own = _parse_percentage(data.get("Inst Own", "0%"))
            short_float = _parse_percentage(data.get("Short Float", "0%"))
            
            # Performance signals
            perf_week = _parse_percentage(data.get("Perf Week", "0%"))
            perf_month = _parse_percentage(data.get("Perf Month", "0%"))
            
            # Calculate sentiment score
            # High insider/inst ownership = bullish signal
            # Low short interest = bullish signal
            # Positive momentum = bullish signal
            
            ownership_score = 0.5
            if insider_own is not None:
                ownership_score += (insider_own - 0.05) * 2  # Baseline 5%
            if inst_own is not None:
                ownership_score += (inst_own - 0.5) * 0.5  # Baseline 50%
            
            short_score = 0.5
            if short_float is not None:
                short_score = max(0.0, 1.0 - short_float * 5)  # High short = bearish
            
            momentum_score = 0.5
            if perf_week is not None:
                momentum_score += perf_week * 2
            if perf_month is not None:
                momentum_score += perf_month * 0.5
            
            # Composite score
            sentiment = max(0.0, min(1.0, ownership_score * 0.4 + short_score * 0.3 + momentum_score * 0.3))
            
            # Buzz based on trading volume and short interest
            volume = _parse_number(data.get("Volume", "0"))
            avg_volume = _parse_number(data.get("Avg Volume", "0"))
            buzz = 0.0
            if volume and avg_volume and avg_volume > 0:
                buzz = min(1.0, volume / avg_volume)
            
            composite = sentiment * 0.6 + buzz * 0.4
            
            results[symbol] = {
                "sentiment_score": round(sentiment, 4),
                "buzz_score": round(buzz, 4),
                "composite_score": round(composite, 4),
                "total_posts": 0,
                "positive_signals": 0,
                "negative_signals": 0,
                "source": "finviz_scrapy",
                "_cache_date": date.today().isoformat(),
                "_details": {
                    "insider_own": insider_own,
                    "inst_own": inst_own,
                    "short_float": short_float,
                    "perf_week": perf_week,
                    "perf_month": perf_month,
                },
            }
    
    # Run spider
    process = CrawlerProcess()
    process.crawl(FinvizSpider, symbols_list=symbols)
    process.start()
    
    return results


def batch_analyze_sentiment(symbols: list[str], use_cache: bool = True) -> dict[str, dict]:
    """Batch analyze sentiment for multiple symbols.
    
    Priority: cache -> finviz_scrapy -> default
    """
    results = {}
    to_fetch = []
    
    # Check cache first
    for sym in symbols:
        cache_key = f"{sym}_{date.today()}.json"
        cache_path = CACHE_DIR / cache_key
        if use_cache and cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                cache_date = cached.get("_cache_date")
                if cache_date and (date.today() - date.fromisoformat(cache_date)).days <= 7:
                    results[sym] = cached
                    continue
            except Exception:
                pass
        to_fetch.append(sym)
    
    if not to_fetch:
        return results
    
    # Fetch from finviz
    try:
        finviz_results = scrape_finviz_batch(to_fetch)
        for sym, data in finviz_results.items():
            results[sym] = data
            to_fetch.remove(sym)
    except Exception as e:
        print(f"Finviz scrape error: {e}")
    
    # Default for any still missing
    for sym in to_fetch:
        results[sym] = {
            "sentiment_score": 0.5,
            "buzz_score": 0.0,
            "composite_score": 0.3,
            "total_posts": 0,
            "positive_signals": 0,
            "negative_signals": 0,
            "source": "default",
            "_cache_date": date.today().isoformat(),
        }
    
    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for sym, data in results.items():
        cache_path = CACHE_DIR / f"{sym}_{date.today()}.json"
        cache_path.write_text(json.dumps(data, ensure_ascii=False))
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch social sentiment scraper")
    parser.add_argument("--symbols", nargs="+", default=["NVDA", "TSLA", "AMD"])
    parser.add_argument("--symbols-from-csv", type=str)
    args = parser.parse_args()
    
    symbols = args.symbols
    if args.symbols_from_csv:
        with open(args.symbols_from_csv) as f:
            reader = csv.DictReader(f)
            symbols = [row["symbol"] for row in reader if "symbol" in row]
    
    results = batch_analyze_sentiment(symbols)
    print(json.dumps(results, indent=2, ensure_ascii=False))
