# US Stock Research Terminal

Research-only US stock ticket pipeline with candidate screening, risk gates, forward tracking, and lifecycle scoreboards. It does not connect to a broker, execute orders, or provide financial advice.

## Demo

```bash
pip install -r requirements.txt
DEMO_MODE=1 uvicorn scripts.api.main:app --reload
```

Open `http://127.0.0.1:8000/api/demo` for fixed sample tickets without credentials, data providers, or a database.

## Architecture

`universe -> research pipeline -> risk manager -> ticket -> forward tracking -> lifecycle scoreboard -> FastAPI`

- Pipeline: `scripts/us_profit_ticket_pipeline.py`
- Risk policy: `scripts/risk_manager.py`
- Scheduler: `scripts/daily_scheduler.py`
- API: `scripts/api/main.py`
- Historical replay: `scripts/historical_replay_baseline.py`

## API

- `GET /api/health`
- `GET /api/tickets`
- `GET /api/scoreboard`
- `GET /api/forward-tracking`
- `GET /api/research-runs`
- `GET /api/demo`

## Validation

```bash
pytest tests -q
python scripts/daily_scheduler.py --dry-run
```

## Limits

The system is intentionally research-only. A public release must remove the tracked `.env`, review data artifacts, and attach a GitHub remote only after the workspace publication audit is cleared.

