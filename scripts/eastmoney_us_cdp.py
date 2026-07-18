"""EastMoney US stock data fetcher via CDP (Chrome DevTools Protocol).

Aligned with xiaogu's approach: CloakBrowser CDP opens EastMoney web pages,
WebSocket extracts DOM data, bypasses push2 API rate limits.

Usage:
    # Start CDP first: bash scripts/start_xiaomei_cdp.sh
    python3 scripts/eastmoney_us_cdp.py --scan          # Full universe scan via CDP
    python3 scripts/eastmoney_us_cdp.py --quote AAPL     # Single quote via CDP
"""
import argparse
import base64
import hashlib
import json
import re
import socket
import struct
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote as urlquote
from typing import Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}
DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

CDP_URL = "http://127.0.0.1:9334"
PUSH2_URL = "https://push2delay.eastmoney.com/api/qt/stock/get"

# EastMoney US stock page URLs (aligned with xiaogu pattern)
US_QUOTE_CENTER_URL = "https://quote.eastmoney.com/center/gridlist.html#us_stocks"


# ── CDP helpers (aligned with xiaogu) ───────────────────────────────

def _http_json(url: str, method: str = "GET", timeout: int = 5) -> Any:
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    with DIRECT_OPENER.open(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8").strip()
    if text and not text.startswith(("{", "[")):
        m = re.search(r"^[^(]+\((.*)\)\s*;?$", text, re.S)
        if m:
            text = m.group(1)
    return json.loads(text)


def cdp_page_tabs(cdp_url: str) -> list[dict]:
    try:
        tabs = _http_json(f"{cdp_url.rstrip('/')}/json")
        return [t for t in tabs if isinstance(t, dict) and t.get("type") == "page"] if isinstance(tabs, list) else []
    except Exception:
        return []


def open_cdp_tab(cdp_url: str, target_url: str) -> dict:
    endpoint = f"{cdp_url.rstrip('/')}/json/new?{urlquote(target_url, safe='')}"
    return _http_json(endpoint, method="PUT")


def _ws_request(ws_url: str, message: dict, timeout: float = 10) -> dict:
    """Send a CDP WebSocket request and return the response. Aligned with xiaogu."""
    parsed = urllib.request.urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    key = base64.b64encode(hashlib.sha1(f"{time.time()}".encode()).digest()[:16]).decode()
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")

    sock = socket.create_connection((host, port), timeout=5)
    sock.settimeout(timeout)
    try:
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = sock.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket upgrade failed: {response[:200]}")

        # Send message
        payload = json.dumps(message).encode("utf-8")
        header = bytearray()
        header.append(0x81)  # FIN + text
        if len(payload) < 126:
            header.append(len(payload))
        elif len(payload) < 65536:
            header.append(126)
            header.extend(struct.pack(">H", len(payload)))
        else:
            header.append(127)
            header.extend(struct.pack(">Q", len(payload)))
        sock.sendall(header + payload)

        # Receive response
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            try:
                # Try to parse - may need multiple frames
                decoded = _ws_decode_frame(data)
                if decoded is not None:
                    return json.loads(decoded)
            except (json.JSONDecodeError, ValueError):
                continue
        return {}
    finally:
        sock.close()


def _ws_decode_frame(data: bytes) -> bytes | None:
    """Decode a single WebSocket frame."""
    if len(data) < 2:
        return None
    opcode = data[0] & 0x0F
    masked = bool(data[1] & 0x80)
    length = data[1] & 0x7F
    offset = 2
    if length == 126:
        if len(data) < 4:
            return None
        length = struct.unpack(">H", data[2:4])[0]
        offset = 4
    elif length == 127:
        if len(data) < 10:
            return None
        length = struct.unpack(">Q", data[2:10])[0]
        offset = 10
    if masked:
        mask = data[offset:offset + 4]
        offset += 4
    if len(data) < offset + length:
        return None
    payload = data[offset:offset + length]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return payload


def _cdp_ws_url_by_tab_id(cdp_url: str, tab_id: str) -> str:
    for tab in cdp_page_tabs(cdp_url):
        if tab.get("id") == tab_id:
            return tab.get("webSocketDebuggerUrl", "")
    return ""


# ── CDP page snapshot (aligned with xiaogu fetch_cdp_page_snapshot) ─

def fetch_cdp_page_snapshot(ws_url: str, target_url: str, wait_sec: float = 3) -> dict:
    """Navigate to URL via CDP, wait, then extract page data via JS evaluation."""
    _ws_request(ws_url, {"id": 1, "method": "Page.navigate", "params": {"url": target_url}})
    time.sleep(wait_sec)
    payload = _ws_request(ws_url, {
        "id": 2,
        "method": "Runtime.evaluate",
        "params": {
            "expression": r"""(() => {
              const visibleText = (el) => (el && el.innerText ? el.innerText.trim() : '');
              const tables = Array.from(document.querySelectorAll('table')).slice(0, 20).map((table, tableIndex) => ({
                table_index: tableIndex,
                rows: Array.from(table.querySelectorAll('tr')).slice(0, 2000).map((tr, rowIndex) => ({
                  row_index: rowIndex,
                  cells: Array.from(tr.querySelectorAll('th,td')).map((td) => visibleText(td)).filter(Boolean)
                })).filter((row) => row.cells.length)
              })).filter((table) => table.rows.length);
              return {url: location.href, title: document.title, text: document.body ? document.body.innerText.slice(0, 50000) : '', tables};
            })()""",
            "returnByValue": True,
            "awaitPromise": True,
        },
    })
    return payload.get("result", {}).get("result", {}).get("value") or {}


# ── Parse CDP DOM data into structured quotes ───────────────────────

def _parse_us_stock_table(snapshot: dict) -> list[dict]:
    """Parse EastMoney US stock table from CDP snapshot into quote dicts.

    EastMoney gridlist table columns: 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, ...
    """
    quotes = []
    for table in snapshot.get("tables", []):
        rows = table.get("rows", [])
        if not rows:
            continue
        # Find header row to identify columns
        header = rows[0].get("cells", [])
        col_map = {}
        for i, cell in enumerate(header):
            cell_lower = cell.strip().lower()
            if "代码" in cell_lower or "code" in cell_lower:
                col_map["code"] = i
            elif "名称" in cell_lower or "name" in cell_lower:
                col_map["name"] = i
            elif "最新价" in cell_lower or "price" in cell_lower:
                col_map["price"] = i
            elif "涨跌幅" in cell_lower or "chg%" in cell_lower or "pct" in cell_lower:
                col_map["pct_chg"] = i
            elif "涨跌额" in cell_lower or "chg" in cell_lower:
                col_map["chg"] = i
            elif "成交量" in cell_lower or "volume" in cell_lower:
                col_map["volume"] = i
            elif "成交额" in cell_lower or "amount" in cell_lower:
                col_map["amount"] = i
            elif "今开" in cell_lower or "open" in cell_lower:
                col_map["open"] = i
            elif "最高" in cell_lower or "high" in cell_lower:
                col_map["high"] = i
            elif "最低" in cell_lower or "low" in cell_lower:
                col_map["low"] = i
            elif "昨收" in cell_lower or "prev" in cell_lower:
                col_map["prev_close"] = i

        if "code" not in col_map or "price" not in col_map:
            continue

        for row in rows[1:]:
            cells = row.get("cells", [])
            if len(cells) <= max(col_map.values()):
                continue
            code = cells[col_map["code"]].strip()
            if not code:
                continue
            price_str = cells[col_map["price"]].strip().replace(",", "")
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue

            def _get(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(cells):
                    v = cells[idx].strip().replace(",", "").replace("%", "")
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        pass
                return None

            quotes.append({
                "symbol": code.replace(".", "-"),
                "name": cells[col_map.get("name", -1)].strip() if col_map.get("name") is not None and col_map["name"] < len(cells) else "",
                "latest_price": price,
                "pct_chg": _get("pct_chg"),
                "chg": _get("chg"),
                "volume": _get("volume"),
                "amount": _get("amount"),
                "open": _get("open"),
                "high": _get("high"),
                "low": _get("low"),
                "prev_close": _get("prev_close"),
                "source": "eastmoney_cdp",
                "as_of": datetime.now().isoformat(),
            })
    return quotes


# ── Public API ──────────────────────────────────────────────────────

def fetch_universe_quotes_cdp(cdp_url: str = CDP_URL, wait_sec: float = 3) -> list[dict]:
    """Fetch full US stock universe from EastMoney via CDP.

    Opens the quote center page in a CDP tab, waits for data to load,
    then extracts all stock data from the DOM table.
    """
    tabs = cdp_page_tabs(cdp_url)
    # Find or create tab with US stock page
    target_tab = None
    for tab in tabs:
        url = tab.get("url", "")
        if "us_stocks" in url or ("gridlist" in url and "us_" in url):
            target_tab = tab
            break

    if not target_tab:
        target_tab = open_cdp_tab(cdp_url, US_QUOTE_CENTER_URL)
        time.sleep(wait_sec)

    ws_url = target_tab.get("webSocketDebuggerUrl", "")
    if not ws_url:
        # Re-fetch tabs to get ws_url
        time.sleep(1)
        tabs = cdp_page_tabs(cdp_url)
        for tab in tabs:
            if tab.get("id") == target_tab.get("id"):
                ws_url = tab.get("webSocketDebuggerUrl", "")
                break

    if not ws_url:
        return []

    snapshot = fetch_cdp_page_snapshot(ws_url, US_QUOTE_CENTER_URL, wait_sec=wait_sec)
    return _parse_us_stock_table(snapshot)


def fetch_realtime_quote_cdp(symbol: str, cdp_url: str = CDP_URL) -> dict[str, Any] | None:
    """Fetch single stock quote via CDP detail page."""
    normalized = symbol.replace(".", "-")
    detail_url = f"https://quote.eastmoney.com/us/{normalized}.html"

    tabs = cdp_page_tabs(cdp_url)
    # Reuse or create a detail tab
    detail_tab = None
    for tab in tabs:
        if f"/us/{normalized.lower()}" in tab.get("url", "").lower():
            detail_tab = tab
            break

    if not detail_tab:
        detail_tab = open_cdp_tab(cdp_url, detail_url)
        time.sleep(2)

    ws_url = detail_tab.get("webSocketDebuggerUrl", "")
    if not ws_url:
        time.sleep(1)
        tabs = cdp_page_tabs(cdp_url)
        for tab in tabs:
            if tab.get("id") == detail_tab.get("id"):
                ws_url = tab.get("webSocketDebuggerUrl", "")
                break
    if not ws_url:
        return None

    snapshot = fetch_cdp_page_snapshot(ws_url, detail_url, wait_sec=2)

    # Extract price from page text
    text = snapshot.get("text", "")
    price_match = re.search(r"(\d+\.?\d*)\s*(?:USD|\$)", text)
    if price_match:
        price = float(price_match.group(1))
        return {
            "symbol": normalized,
            "latest_price": price,
            "source": "eastmoney_cdp_detail",
            "as_of": datetime.now().isoformat(),
        }
    return None


def fetch_realtime_quotes(symbols: list[str], delay: float = 0.3) -> dict[str, dict]:
    """Batch fetch realtime quotes via push2 API (fallback when CDP not available)."""
    results = {}
    for sym in symbols:
        normalized = sym.replace(".", "-")
        for secid in [f"105.{normalized}", f"106.{normalized}"]:
            params = {
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fltt": "2", "invt": "2",
                "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f84,f85,f162,f167,f173,f191",
                "secid": secid,
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            try:
                req = urllib.request.Request(f"{PUSH2_URL}?{query}", headers=HEADERS)
                resp = DIRECT_OPENER.open(req, timeout=8)
                payload = json.loads(resp.read())
                if payload.get("data"):
                    d = payload["data"]
                    latest = d.get("f43")
                    if latest is not None and latest != "-":
                        results[sym] = {
                            "symbol": normalized,
                            "name": d.get("f58", ""),
                            "latest_price": float(latest),
                            "prev_close": float(d.get("f60", 0)),
                            "open": float(d.get("f46", 0)) if d.get("f46") != "-" else None,
                            "high": float(d.get("f44", 0)) if d.get("f44") != "-" else None,
                            "low": float(d.get("f45", 0)) if d.get("f45") != "-" else None,
                            "volume": float(d.get("f47", 0)) if d.get("f47") != "-" else None,
                            "source": "eastmoney_push2",
                            "as_of": datetime.now().isoformat(),
                        }
                        break
            except Exception:
                pass
        if delay > 0:
            time.sleep(delay)
    return results


# ── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EastMoney US stock CDP fetcher")
    parser.add_argument("--scan", action="store_true", help="Full universe scan via CDP")
    parser.add_argument("--quote", help="Single symbol quote via CDP")
    parser.add_argument("--cdp-url", default=CDP_URL)
    parser.add_argument("--output-dir", help="Output directory for scan results")
    args = parser.parse_args()

    if args.scan:
        print(f"Scanning US stocks via CDP ({args.cdp_url})...")
        quotes = fetch_universe_quotes_cdp(args.cdp_url)
        print(f"Got {len(quotes)} quotes")

        if quotes:
            out_dir = Path(args.output_dir) if args.output_dir else Path("data/live_scan") / datetime.now().strftime("%Y-%m-%d") / "cdp_us_scan"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "us_quotes.jsonl"
            with open(out_path, "w") as f:
                for q in quotes:
                    f.write(json.dumps(q, ensure_ascii=False) + "\n")
            print(f"Saved to {out_path}")

            summary = {
                "source": "eastmoney_cdp_us_scan",
                "count": len(quotes),
                "cdp_url": args.cdp_url,
                "timestamp": datetime.now().isoformat(),
            }
            (out_dir / "cdp_scan_summary.json").write_text(json.dumps(summary, indent=2))
    elif args.quote:
        q = fetch_realtime_quote_cdp(args.quote, args.cdp_url)
        if q:
            print(json.dumps(q, indent=2, ensure_ascii=False))
        else:
            print(f"No data for {args.quote}")
    else:
        parser.print_help()
