#!/bin/bash
# xiaomei infrastructure startup
# Portfolio coexistence: PostgreSQL on 5432 (xiaogu owns 5432).
# Prefer docker-fallback xiaomei-db; Redis still native 6379.

set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== xiaomei infrastructure startup ==="

if [ -f "$ROOT/.env" ]; then
    set -a
    . "$ROOT/.env"
    set +a
fi

: "${DATABASE_URL:?DATABASE_URL must be set in the environment or .env}"
DB_URL="$DATABASE_URL"
DB_PORT=5432

if pg_isready -h 127.0.0.1 -p "$DB_PORT" -q 2>/dev/null; then
    echo "PostgreSQL: already accepting on $DB_PORT"
else
    echo "PostgreSQL: starting xiaomei-db (docker-fallback, port $DB_PORT)..."
    if docker-compose --profile docker-fallback up -d xiaomei-db; then
        for i in 1 2 3 4 5 6 7 8 9 10; do
            if pg_isready -h 127.0.0.1 -p "$DB_PORT" -q 2>/dev/null; then
                break
            fi
            sleep 1
        done
    fi
    if pg_isready -h 127.0.0.1 -p "$DB_PORT" -q 2>/dev/null; then
        echo "PostgreSQL: ready on $DB_PORT"
    else
        echo "PostgreSQL: FAILED on $DB_PORT"
        exit 1
    fi
fi

if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "Redis: already running (port 6379)"
else
    echo "Redis: starting..."
    redis-server --port 6379 --daemonize yes --loglevel warning 2>/dev/null || true
    sleep 1
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "Redis: started (port 6379)"
    else
        echo "Redis: WARN not running (optional for pure DB migrate)"
    fi
fi

if psql "$DB_URL" -c "SELECT 1" >/dev/null 2>&1; then
    echo "Database 'xiaomei': accessible on $DB_PORT"
else
    echo "Database 'xiaomei': waiting for role/db init..."
    sleep 2
    if psql "$DB_URL" -c "SELECT 1" >/dev/null 2>&1; then
        echo "Database 'xiaomei': accessible"
    else
        echo "Database 'xiaomei': NOT ready — check docker logs xiaomei-db"
        exit 1
    fi
fi

SCHEDULER_LOG_FILE="$ROOT/logs/xiaomei_scheduler.log"

if python3 "$ROOT/scripts/xiaomei_scheduler.py" --scheduler-status >/dev/null 2>&1; then
    echo "Scheduler: already running"
else
    mkdir -p "$ROOT/run" "$(dirname "$SCHEDULER_LOG_FILE")"
    setsid --fork python3 "$ROOT/scripts/xiaomei_scheduler.py" --daemon \
        </dev/null >> "$SCHEDULER_LOG_FILE" 2>&1 &
    for _ in 1 2 3; do
        sleep 1
        if python3 "$ROOT/scripts/xiaomei_scheduler.py" --scheduler-status >/dev/null 2>&1; then
            echo "Scheduler: started and verified"
            break
        fi
    done
    if ! python3 "$ROOT/scripts/xiaomei_scheduler.py" --scheduler-status >/dev/null 2>&1; then
        echo "Scheduler: FAILED liveness verification"
        exit 1
    fi
fi

echo "=== Infrastructure ready (DB $DB_PORT) ==="
