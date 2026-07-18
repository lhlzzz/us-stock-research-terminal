# TOOLING

- Market data source: EastMoney US realtime/delayed quote + kline provider via `scripts/eastmoney_us.py` only.
- `last30days` is public-source social/narrative research only, not a price source.
- Crypto work stays research-only; no exchange API, wallet, or broker feed.
- No uSMART / 盈立 login, no EastMoney login, no paid market data API, no broker account access, no order/ledger/live-trade path.
- `quant-python` command used in this workspace:
  - `/root/hermes/company-ai-system/tools/external/bin/quant-python workspaces/xiaomei/scripts/us_profit_ticket_pipeline.py --help`
- EastMoney requests are direct provider reads with rate-limit delay; no legacy market-data source proxy path is part of the current runtime.
- `last30days` run is for public narrative only and should not be treated as execution signal.
