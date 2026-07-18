#!/usr/bin/env python3
"""Capture EastMoney kline images via CDP and extract OHLCV data using vision.

Workflow:
1. Navigate CDP browser to EastMoney US stock page
2. Screenshot the kline chart area
3. Use multimodal AI to read OHLCV data from the image
4. Store in daily_klines table
"""
import json
import sys
import time
import base64
import urllib.request
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.db.engine import SessionLocal
from scripts.db.crud import upsert_kline

CDP_URL = "http://localhost:9333"
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kline-screenshots"


def get_cdp_ws_url():
    """Get the websocket URL for the CDP browser."""
    try:
        resp = urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=5)
        version = json.loads(resp.read())
        return version.get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"Cannot connect to CDP: {e}")
        return None


def get_dal_tab_ws():
    """Get websocket URL for the DAL tab (or any US stock tab)."""
    try:
        resp = urllib.request.urlopen(f"{CDP_URL}/json/list", timeout=5)
        tabs = json.loads(resp.read())
        for tab in tabs:
            url = tab.get("url", "")
            if "eastmoney.com/us/" in url or "eastmoney.com/center/gridlist" in url:
                return tab.get("webSocketDebuggerUrl")
        # Use first tab if no EastMoney tab found
        if tabs:
            return tabs[0].get("webSocketDebuggerUrl")
    except Exception:
        pass
    return None


def capture_kline_screenshot(symbol: str) -> str | None:
    """Navigate to stock page and capture kline chart screenshot."""
    import websocket

    ws_url = get_dal_tab_ws()
    if not ws_url:
        ws_url = get_cdp_ws_url()
    if not ws_url:
        print("No CDP connection available")
        return None

    ws = websocket.create_connection(ws_url, timeout=15)
    msg_id = 1

    def send_cmd(method, params=None):
        nonlocal msg_id
        cmd = {"id": msg_id, "method": method}
        if params:
            cmd["params"] = params
        ws.send(json.dumps(cmd))
        msg_id += 1
        return json.loads(ws.recv())

    # Navigate to stock page
    send_cmd("Page.navigate", {"url": f"https://quote.eastmoney.com/us/{symbol}.html"})
    time.sleep(4)

    # Take full page screenshot
    result = send_cmd("Page.captureScreenshot", {"format": "png"})
    img_data = result.get("result", {}).get("data")
    if not img_data:
        ws.close()
        return None

    # Save screenshot
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SCREENSHOT_DIR / f"{symbol}_kline_{date.today()}.png"
    filepath.write_bytes(base64.b64decode(img_data))
    ws.close()
    return str(filepath)


def extract_kline_from_screenshot(filepath: str, symbol: str) -> list[dict]:
    """Use vision to extract OHLCV data from kline screenshot.

    This function reads the screenshot and returns kline data.
    In production, this would call a multimodal AI API.
    For now, we parse the image locally or return empty.
    """
    # The actual vision extraction would happen here
    # For now, we'll try to extract data from the page's DOM instead
    return []


def extract_kline_via_cdp(symbol: str) -> list[dict]:
    """Extract kline data from the EastMoney page DOM via CDP."""
    import websocket

    ws_url = get_dal_tab_ws()
    if not ws_url:
        ws_url = get_cdp_ws_url()
    if not ws_url:
        return []

    ws = websocket.create_connection(ws_url, timeout=15)
    msg_id = 1

    def send_cmd(method, params=None):
        nonlocal msg_id
        cmd = {"id": msg_id, "method": method}
        if params:
            cmd["params"] = params
        ws.send(json.dumps(cmd))
        msg_id += 1
        return json.loads(ws.recv())

    # Navigate to stock page
    send_cmd("Page.navigate", {"url": f"https://quote.eastmoney.com/us/{symbol}.html"})
    time.sleep(5)

    # Try to extract data from the page's table or chart
    result = send_cmd("Runtime.evaluate", {
        "expression": """
            (function() {
                // Look for kline data table in the page
                var tables = document.querySelectorAll('table');
                for (var i = 0; i < tables.length; i++) {
                    var rows = tables[i].querySelectorAll('tr');
                    if (rows.length > 5) {
                        var data = [];
                        for (var j = 1; j < rows.length; j++) {
                            var cells = rows[j].querySelectorAll('td');
                            if (cells.length >= 5) {
                                data.push({
                                    date: cells[0].textContent.trim(),
                                    open: cells[1].textContent.trim(),
                                    close: cells[2].textContent.trim(),
                                    high: cells[3].textContent.trim(),
                                    low: cells[4].textContent.trim(),
                                    volume: cells[5] ? cells[5].textContent.trim() : ''
                                });
                            }
                        }
                        if (data.length > 0) return JSON.stringify(data);
                    }
                }
                return '[]';
            })()
        """
    })

    value = result.get("result", {}).get("result", {}).get("value", "[]")
    try:
        klines = json.loads(value)
        ws.close()
        return klines
    except json.JSONDecodeError:
        ws.close()
        return []


def save_klines_to_db(symbol: str, klines: list[dict]) -> int:
    """Save extracted kline data to daily_klines table."""
    db = SessionLocal()
    count = 0
    try:
        for k in klines:
            try:
                trade_date_str = k.get("date", "")
                if not trade_date_str or len(trade_date_str) < 10:
                    continue
                trade_date = date.fromisoformat(trade_date_str[:10])

                def to_float(v):
                    if not v or v == "-" or v == "":
                        return None
                    try:
                        return float(v.replace(",", ""))
                    except (ValueError, TypeError):
                        return None

                def to_int(v):
                    if not v or v == "-" or v == "":
                        return None
                    try:
                        return int(float(v.replace(",", "")))
                    except (ValueError, TypeError):
                        return None

                upsert_kline(db, symbol, trade_date,
                    open=to_float(k.get("open")),
                    high=to_float(k.get("high")),
                    low=to_float(k.get("low")),
                    close=to_float(k.get("close")),
                    adj_close=to_float(k.get("close")),
                    volume=to_int(k.get("volume")),
                    source="eastmoney_cdp_image")
                count += 1
            except Exception:
                continue
    finally:
        db.close()
    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Capture and extract kline data from EastMoney via CDP")
    parser.add_argument("--symbol", default="DAL", help="Stock symbol to capture")
    parser.add_argument("--screenshot-only", action="store_true", help="Only take screenshot, don't extract")
    parser.add_argument("--extract-only", action="store_true", help="Only extract from page DOM")
    args = parser.parse_args()

    symbol = args.symbol.upper()

    if args.extract_only:
        print(f"Extracting kline data from page DOM for {symbol}...")
        klines = extract_kline_via_cdp(symbol)
        print(f"  Found {len(klines)} klines")
        if klines:
            count = save_klines_to_db(symbol, klines)
            print(f"  Saved {count} rows to database")
        return

    print(f"Capturing kline screenshot for {symbol}...")
    filepath = capture_kline_screenshot(symbol)
    if filepath:
        print(f"  Screenshot saved: {filepath}")
    else:
        print("  Screenshot failed")

    if not args.screenshot_only:
        print(f"Extracting kline data from page DOM for {symbol}...")
        klines = extract_kline_via_cdp(symbol)
        print(f"  Found {len(klines)} klines")
        if klines:
            count = save_klines_to_db(symbol, klines)
            print(f"  Saved {count} rows to database")


if __name__ == "__main__":
    main()
