"""Celery application configuration for xiaomei."""
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")

app = Celery("xiaomei", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="US/Eastern",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "scripts.tasks.kline_tasks.*": {"queue": "kline"},
        "scripts.tasks.pipeline_tasks.*": {"queue": "pipeline"},
        "scripts.tasks.backfill_tasks.*": {"queue": "backfill"},
    },
    beat_schedule={
        "fetch-daily-klines": {
            "task": "scripts.tasks.kline_tasks.fetch_daily_klines",
            "schedule": None,
        },
    },
)

app.autodiscover_tasks(["scripts.tasks"])
