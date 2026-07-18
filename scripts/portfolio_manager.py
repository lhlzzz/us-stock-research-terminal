#!/usr/bin/env python3
"""Portfolio diversification checker."""
from collections import Counter


SECTOR_KEYWORDS = {
    "Technology": ["tech", "software", "semiconductor", "chip", "cloud", "cyber", "saas", "data", "digital", "ai", "network"],
    "Healthcare": ["pharma", "bio", "medical", "health", "drug", "clinical"],
    "Financial": ["bank", "capital", "insurance", "financial", "securities", "investment"],
    "Consumer Cyclical": ["retail", "consumer", "ecommerce", "travel", "leisure", "restaurant", "hotel", "airline"],
    "Industrials": ["industrial", "manufacturing", "aerospace", "defense", "engineering", "transport"],
    "Communication": ["media", "entertainment", "streaming", "telecom", "advertising"],
    "Consumer Defensive": ["food", "beverage", "household", "staples"],
    "Utilities": ["electric", "utility", "water"],
    "Real Estate": ["reit", "property", "real estate", "trust"],
    "Materials": ["mining", "chemical", "steel", "lithium", "material"],
}

MAX_PER_SECTOR = 3


def infer_sector(symbol: str) -> str:
    name_lower = symbol.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return sector
    return "Unknown"


def check_portfolio_diversification(candidates: list[dict]) -> dict:
    sectors = [c.get("sector") or infer_sector(c["symbol"]) for c in candidates]
    sector_counts = Counter(sectors)
    warnings = []
    for sector, count in sector_counts.items():
        if count > MAX_PER_SECTOR:
            warnings.append(f"{sector}: {count} candidates (max {MAX_PER_SECTOR})")
    diversified = len(warnings) == 0
    return {"diversified": diversified, "sector_counts": dict(sector_counts), "warnings": warnings}


def suggest_replacements(blocked_symbols: list, universe_symbols: list, existing_sectors: dict) -> list:
    overrepresented = {s for s, c in existing_sectors.items() if c > MAX_PER_SECTOR}
    suggestions = []
    for sym in universe_symbols:
        if sym in blocked_symbols:
            continue
        sector = infer_sector(sym)
        if sector not in overrepresented and sector != "Unknown":
            suggestions.append({"symbol": sym, "sector": sector})
            if len(suggestions) >= 5:
                break
    return suggestions
