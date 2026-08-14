#!/bin/bash
# xiaomei infrastructure startup
# Portfolio coexistence: PostgreSQL on 5432 (xiaogu owns 5432).
# Prefer docker-fallback xiaomei-db; Redis still native 6379.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== xiaomei infrastructure startup ==="

DB_URL="${DATABASE_URL:-postgresql://xiaomei:xiaomei2026@localhost:5432/xiaomei}"
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

if PGPASSWORD=xiaomei2026 psql -U xiaomei -h 127.0.0.1 -p "$DB_PORT" -d xiaomei -c "SELECT 1" >/dev/null 2>&1; then
    echo "Database 'xiaomei': accessible on $DB_PORT"
else
    echo "Database 'xiaomei': waiting for role/db init..."
    sleep 2
    if PGPASSWORD=xiaomei2026 psql -U xiaomei -h 127.0.0.1 -p "$DB_PORT" -d xiaomei -c "SELECT 1" >/dev/null 2>&1; then
        echo "Database 'xiaomei': accessible"
    else
        echo "Database 'xiaomei': NOT ready — check docker logs xiaomei-db"
        exit 1
    fi
fi

SCHEDULER_PID_FILE="$ROOT/run/xiaomei_scheduler.pid"
SCHEDULER_LOG_FILE="$ROOT/logs/xiaomei_scheduler.log"
SCHEDULER_PID="$(pgrep -f 'python3 .*scripts/xiaomei_scheduler.py --daemon' | head -n 1 || true)"

if [ -n "$SCHEDULER_PID" ]; then
    mkdir -p "$(dirname "$SCHEDULER_PID_FILE")"
    echo "$SCHEDULER_PID" > "$SCHEDULER_PID_FILE"
    echo "Scheduler: already running (pid $SCHEDULER_PID)"
else
    mkdir -p "$(dirname "$SCHEDULER_PID_FILE")" "$(dirname "$SCHEDULER_LOG_FILE")"
    nohup python3 "$ROOT/scripts/xiaomei_scheduler.py" --daemon >> "$SCHEDULER_LOG_FILE" 2>&1 &
    SCHEDULER_PID=$!
    sleep 1
    if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
        echo "$SCHEDULER_PID" > "$SCHEDULER_PID_FILE"
        echo "Scheduler: started (pid $SCHEDULER_PID)"
    else
        echo "Scheduler: FAILED to start"
        exit 1
    fi
fi

echo "=== Infrastructure ready (DB $DB_PORT) ==="
