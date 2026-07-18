# xiaomei yfinance smoke summary

## Proxy / network
- `HTTP_PROXY` / `HTTPS_PROXY` point to `http://127.0.0.1:7897`
- proxy socket is open outside sandbox
- direct no-proxy DNS path is not usable from sandboxed shell

## Yahoo endpoint diagnosis
- `query1.finance.yahoo.com` direct GET: `403` HTML sad-panda block
- `query2.finance.yahoo.com` direct GET: `403` HTML sad-panda block
- proxy-backed `query1` GET: `429 Too Many Requests`
- proxy-backed `query2` GET: `429 Too Many Requests`

## yfinance diagnosis
- version: `1.4.1`
- cache dir: `~/.cache/py-yfinance`
- cache files: `cookies.db`, `tkr-tz.db`
- AAPL `period=5d`: PASS on retry, 5 rows

## Rows per symbol
- AAPL: 124 rows
- MSFT: 124 rows
- NVDA: 124 rows
- META: 124 rows
- AMZN: 124 rows
- TSLA: 124 rows

## Conclusion
`yfinance` is usable for research-only smoke through the existing proxy. Short-range direct Yahoo probes still hit `403/429`, so historical replay work should stay proxy-backed.
