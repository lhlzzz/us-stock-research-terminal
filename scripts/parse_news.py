#!/usr/bin/env python3
"""Parse Google News HTML to extract article data."""

import json
import re
from pathlib import Path

RESEARCH_DIR = Path("/root/hermes/company-ai-system/workspaces/xiaomei/research/last30days-2026-06-18")


def parse_google_news_html(html: str) -> list[dict]:
    """Extract articles from Google News HTML."""
    articles = []
    
    title_pattern = r'<a[^>]*href="(/articles/[^"]*)"[^>]*>([^<]+)</a>'
    titles = re.findall(title_pattern, html)
    
    time_pattern = r'<time[^>]*datetime="([^"]*)"[^>]*>'
    times = re.findall(time_pattern, html)
    
    source_pattern = r'<span[^>]*data-n-tid[^>]*>([^<]+)</span>'
    sources = re.findall(source_pattern, html)
    
    for i, (url, title) in enumerate(titles[:10]):
        article = {
            "title": title.strip(),
            "url": f"https://news.google.com{url}" if url.startswith("/") else url,
            "time": times[i] if i < len(times) else "",
            "source": sources[i] if i < len(sources) else "",
        }
        articles.append(article)
    
    return articles


def extract_headlines_from_html(html: str) -> list[dict]:
    """Alternative: extract headlines using simpler patterns."""
    articles = []
    
    patterns = [
        r'"headline"\s*:\s*"([^"]+)"',
        r'"title"\s*:\s*"([^"]+)"',
        r'<h[1-4][^>]*>([^<]+)</h[1-4]>',
    ]
    
    seen_titles = set()
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for title in matches:
            title = title.strip()
            if len(title) > 20 and title not in seen_titles and "Google" not in title:
                seen_titles.add(title)
                articles.append({"title": title, "source": "google_news"})
    
    return articles[:15]


def main():
    results = {}
    
    for ticker in ["wdc", "stx", "ual", "ter", "amat"]:
        news_file = RESEARCH_DIR / f"{ticker}-news.json"
        if not news_file.exists():
            continue
        
        data = json.loads(news_file.read_text())
        html = data.get("news_fetch", {}).get("preview", "")
        
        articles = extract_headlines_from_html(html)
        
        results[ticker.upper()] = {
            "name": data.get("name", ""),
            "article_count": len(articles),
            "articles": articles[:10],
        }
        
        print(f"\n=== {ticker.upper()} ({data.get('name', '')}) ===")
        print(f"Found {len(articles)} headlines")
        for i, art in enumerate(articles[:5], 1):
            print(f"  {i}. {art['title'][:80]}")
    
    output_file = RESEARCH_DIR / "parsed-news.json"
    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nParsed: {output_file}")


if __name__ == "__main__":
    main()
