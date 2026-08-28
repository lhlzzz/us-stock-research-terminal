#!/usr/bin/env python3
"""Analyze underperforming symbols to understand what's dragging returns."""

import csv
import glob
import json
from pathlib import Path
from collections import defaultdict

CAPITAL_FAILURE_TAXONOMY = (
    "FALSE_ACCUMULATION",
    "FALSE_ABSORPTION",
    "DISTRIBUTION_MISSED",
    "FALSE_MARKUP",
    "SHORT_PRESSURE_MISSED",
    "SHORT_COVER_MISSED",
    "TRAP_MISSED",
    "REGIME_SHIFT",
    "NEWS_SHOCK",
    "LIQUIDITY_FAILURE",
    "DATA_FAILURE",
    "STATE_TRANSITION_FAILURE",
)


def classify_capital_failure(candidate, forward_return):
    """Classify observable model failure without asserting participant identity."""
    if not candidate:
        return "DATA_FAILURE"
    if str(candidate.get("trap_score", "0") or "0") not in {"", "0"}:
        try:
            if float(candidate["trap_score"]) >= 0.70:
                return "TRAP_MISSED"
        except ValueError:
            return "DATA_FAILURE"
    if str(candidate.get("distribution_score", "0") or "0") not in {"", "0"}:
        try:
            if float(candidate["distribution_score"]) >= 0.70:
                return "DISTRIBUTION_MISSED"
        except ValueError:
            return "DATA_FAILURE"
    state = candidate.get("capital_state", "")
    if state == "ACCUMULATION":
        return "FALSE_ACCUMULATION"
    if state == "PULLBACK_ABSORPTION":
        return "FALSE_ABSORPTION"
    if state in {"ACTIVE_MARKUP", "SECONDARY_MARKUP", "LATE_MARKUP"}:
        return "FALSE_MARKUP"
    if state in {"SHORT_BUILD", "SHORT_PRESSURE"} and forward_return > 0:
        return "SHORT_COVER_MISSED"
    return "STATE_TRANSITION_FAILURE"


def extract_forward_tracking_data(research_dir):
    """Extract all completed forward tracking rows."""
    rows = []
    for csv_file in glob.glob(f"{research_dir}/**/forward-tracking-*.csv", recursive=True):
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('check_status') == 'completed' and row.get('forward_return'):
                        try:
                            row['forward_return'] = float(row['forward_return'])
                            row['horizon_days'] = int(row['horizon_days'])
                            row['source_file'] = csv_file
                            rows.append(row)
                        except (ValueError, KeyError):
                            continue
        except Exception as e:
            continue
    return rows

def extract_candidate_data(research_dir):
    """Extract candidate data for symbols."""
    candidates = {}
    for csv_file in glob.glob(f"{research_dir}/**/candidates-*.csv", recursive=True):
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get('symbol')
                    if symbol and symbol not in candidates:
                        candidates[symbol] = row
        except Exception:
            continue
    return candidates

def analyze_performance(rows):
    """Analyze performance by symbol."""
    symbol_stats = defaultdict(lambda: {'returns': [], 'horizons': defaultdict(list)})
    
    for row in rows:
        symbol = row['symbol']
        ret = row['forward_return']
        horizon = row['horizon_days']
        
        symbol_stats[symbol]['returns'].append(ret)
        symbol_stats[symbol]['horizons'][horizon].append(ret)
    
    # Calculate stats
    results = []
    for symbol, stats in symbol_stats.items():
        returns = stats['returns']
        if not returns:
            continue
            
        avg_return = sum(returns) / len(returns)
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        
        horizon_stats = {}
        for horizon, h_returns in stats['horizons'].items():
            horizon_stats[horizon] = {
                'count': len(h_returns),
                'avg_return': sum(h_returns) / len(h_returns),
                'win_rate': sum(1 for r in h_returns if r > 0) / len(h_returns)
            }
        
        results.append({
            'symbol': symbol,
            'total_trades': len(returns),
            'avg_return': avg_return,
            'win_rate': win_rate,
            'horizon_stats': horizon_stats
        })
    
    # Sort by avg_return
    results.sort(key=lambda x: x['avg_return'])
    return results

def main():
    research_dir = Path(__file__).resolve().parent.parent / "research"
    
    print("=== Analyzing Forward Tracking Data ===")
    rows = extract_forward_tracking_data(research_dir)
    print(f"Found {len(rows)} completed forward tracking rows")
    
    if not rows:
        print("No completed rows found")
        return
    
    # Analyze performance
    results = analyze_performance(rows)
    
    print("\n=== Performance by Symbol (sorted by avg_return) ===")
    print(f"{'Symbol':<10} {'Trades':<8} {'Avg Return':<12} {'Win Rate':<10}")
    print("-" * 50)
    
    for r in results:
        print(f"{r['symbol']:<10} {r['total_trades']:<8} {r['avg_return']:+.2%}{'':<6} {r['win_rate']:.1%}")
    
    # Focus on losers
    losers = [r for r in results if r['avg_return'] < 0]
    if losers:
        print(f"\n=== Top Losers (Avg Return < 0) ===")
        for r in losers[:10]:
            print(f"\n{r['symbol']}:")
            print(f"  Total trades: {r['total_trades']}")
            print(f"  Avg return: {r['avg_return']:+.2%}")
            print(f"  Win rate: {r['win_rate']:.1%}")
            
            if r['horizon_stats']:
                print("  By horizon:")
                for horizon, stats in sorted(r['horizon_stats'].items()):
                    print(f"    {horizon}d: {stats['count']} trades, avg {stats['avg_return']:+.2%}, win {stats['win_rate']:.1%}")
    
    # Extract candidate data for losers
    print("\n=== Candidate Data for Losers ===")
    candidates = extract_candidate_data(research_dir)
    post_mortems = []
    
    for r in losers[:5]:
        symbol = r['symbol']
        if symbol in candidates:
            c = candidates[symbol]
            print(f"\n{symbol}:")
            print(f"  Market score: {c.get('market_score', 'N/A')}")
            print(f"  Catalyst score: {c.get('catalyst_score', 'N/A')}")
            print(f"  Ticket score: {c.get('ticket_score', 'N/A')}")
            print(f"  Quality: {c.get('quality', 'N/A')}")
            print(f"  Risk: {c.get('risk', 'N/A')}")
            print(f"  Panel: {c.get('panel', 'N/A')}")
            print(f"  Narrative: {c.get('narrative_status', 'N/A')}")
            print(f"  Business: {c.get('business_status', 'N/A')}")
            classification = classify_capital_failure(c, r["avg_return"])
            post_mortems.append({
                "symbol": symbol,
                "prediction": {
                    "capital_state": c.get("capital_state"),
                    "capital_intent": c.get("capital_intent"),
                    "predicted_path": c.get("predicted_path") or c.get("path_type"),
                },
                "actual_state": "UNAVAILABLE_FROM_CSV",
                "missed_evidence": "UNAVAILABLE_FROM_CSV",
                "failure_taxonomy": classification,
                "why_transition_was_wrong": classification,
                "which_feature_failed": "UNAVAILABLE_FROM_CSV",
                "which_gate_failed": "UNAVAILABLE_NO_PRODUCTION_GATE",
            })
    if post_mortems:
        output = research_dir / "capital-post-mortem.json"
        output.write_text(json.dumps({
            "status": "RESEARCH_ONLY",
            "taxonomy": CAPITAL_FAILURE_TAXONOMY,
            "post_mortems": post_mortems,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nCapital post mortem: {output}")

if __name__ == "__main__":
    main()
