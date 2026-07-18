#!/usr/bin/env python3
"""Fetch stock news using CloakBrowser to bypass anti-scraping."""

import json
import subprocess
import sys
import time
from pathlib import Path

RESEARCH_DIR = Path("/root/hermes/company-ai-system/workspaces/xiaomei/research/last30days-2026-06-18")
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

STOCKS = [
    {"ticker": "WDC", "name": "Western Digital"},
    {"ticker": "STX", "name": "Seagate Technology"},
    {"ticker": "UAL", "name": "United Airlines"},
    {"ticker": "TER", "name": "Teradyne"},
    {"ticker": "AMAT", "name": "Applied Materials"},
]

def fetch_news_with_cloakbrowser(query: str, save_path: Path) -> dict:
    """Use CloakBrowser CDP to fetch news from Google."""
    js_code = f"""
    async (page) => {{
        const url = 'https://news.google.com/search?q={query.replace(" ", "+")}&hl=en-US&gl=US&ceid=US:en';
        await page.goto(url, {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
        await page.waitForTimeout(3000);
        
        const articles = await page.evaluate(() => {{
            const items = document.querySelectorAll('article');
            return Array.from(items).slice(0, 10).map(article => {{
                const titleEl = article.querySelector('a[href]');
                const timeEl = article.querySelector('time');
                const sourceEl = article.querySelector('[data-n-tid]');
                return {{
                    title: titleEl ? titleEl.textContent.trim() : '',
                    url: titleEl ? titleEl.href : '',
                    time: timeEl ? timeEl.getAttribute('datetime') || timeEl.textContent : '',
                    source: sourceEl ? sourceEl.textContent.trim() : '',
                }};
            }});
        }});
        
        return articles;
    }}
    """
    
    try:
        result = subprocess.run(
            ["cloakbrowser", "run", "--headless", "--javascript", js_code],
            capture_output=True,
            text=True,
            timeout=60,
            env={**dict(__import__("os").environ)}
        )
        if result.returncode == 0:
            return {"status": "ok", "articles": json.loads(result.stdout) if result.stdout.strip() else []}
        else:
            return {"status": "error", "error": result.stderr[:500]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:500]}


def fetch_news_via_http(query: str) -> dict:
    """Fallback: fetch news via HTTP request."""
    import urllib.request
    import urllib.parse
    
    url = f"https://news.google.com/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8")
            return {"status": "ok", "html_length": len(html), "preview": html[:2000]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:500]}


def main():
    results = {}
    
    for stock in STOCKS:
        ticker = stock["ticker"]
        name = stock["name"]
        query = f"{ticker} {name} stock earnings news 2026"
        
        print(f"\n=== {ticker} ({name}) ===")
        
        news = fetch_news_via_http(query)
        results[ticker] = {
            "name": name,
            "query": query,
            "news_fetch": news,
        }
        
        save_path = RESEARCH_DIR / f"{ticker.lower()}-news.json"
        save_path.write_text(json.dumps(results[ticker], indent=2, ensure_ascii=False))
        print(f"  Status: {news['status']}")
        if news["status"] == "ok":
            print(f"  HTML length: {news.get('html_length', 0)}")
        else:
            print(f"  Error: {news.get('error', 'unknown')[:100]}")
        
        time.sleep(1)
    
    summary_path = RESEARCH_DIR / "news-summary.json"
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nSummary: {summary_path}")


if __name__ == "__main__":
    main()
