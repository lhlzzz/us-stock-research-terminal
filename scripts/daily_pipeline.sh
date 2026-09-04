#!/bin/bash
# xiaomei daily pipeline - single authoritative chain
# Aligned with xiaogu's daily_pipeline.sh architecture
#
# Timeline (Beijing time):
#   04:00  US market closes (summer)
#   05:00  Safe to run pipeline (after US close)
#   21:30  US market opens (summer)
#
# Usage:
#   ./daily_pipeline.sh              # Full pipeline
#   ./daily_pipeline.sh --backfill   # Backfill only
#   ./daily_pipeline.sh --tickets    # Tickets only
#   ./daily_pipeline.sh --knowledge  # Knowledge export only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    . "$PROJECT_DIR/.env"
    set +a
fi

: "${DATABASE_URL:?DATABASE_URL must be set in the environment or .env}"

DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/pipeline-$DATE.log"
LOCK_DIR="$PROJECT_DIR/run/daily-pipeline.lock"
STATE_DIR="$PROJECT_DIR/run/pipeline-state/$DATE"
RUN_ID="${DATE}-$(date +%H%M%S)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

acquire_lock() {
    mkdir -p "$PROJECT_DIR/run"
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        if [ -f "$LOCK_DIR/pid" ] && kill -0 "$(cat "$LOCK_DIR/pid")" 2>/dev/null; then
            log "ERROR: daily pipeline already running (pid $(cat "$LOCK_DIR/pid"))"
            exit 1
        fi
        rm -rf "$LOCK_DIR"
        mkdir "$LOCK_DIR"
    fi
    echo $$ > "$LOCK_DIR/pid"
    echo "$RUN_ID" > "$LOCK_DIR/run_id"
    trap 'rm -rf "$LOCK_DIR"' EXIT
}

step_state() {
    local step_id="$1"
    local status="$2"
    mkdir -p "$STATE_DIR"
    local now
    now="$(date --iso-8601=seconds)"
    local file="$STATE_DIR/${step_id}.json"
    local artifact_hash
    artifact_hash="$(printf '%s|%s|%s' "$RUN_ID" "$step_id" "$status" | sha256sum | awk '{print $1}')"
    if [ "$status" = "started" ]; then
        printf '{"run_id":"%s","step_id":"%s","step_status":"started","started_at":"%s","completed_at":null,"artifact_hash":"%s"}\n' \
            "$RUN_ID" "$step_id" "$now" "$artifact_hash" > "$file"
        return
    fi
    printf '{"run_id":"%s","step_id":"%s","step_status":"%s","completed_at":"%s","artifact_hash":"%s"}\n' \
        "$RUN_ID" "$step_id" "$status" "$now" "$artifact_hash" > "$file"
}

check_services() {
    log "Checking infrastructure..."
    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log "PostgreSQL not ready, attempting start..."
        bash "$PROJECT_DIR/scripts/start_services.sh" || true
    fi
    if ! redis-cli ping >/dev/null 2>&1; then
        log "Redis not ready, attempting start..."
        redis-server --daemonize yes 2>/dev/null || true
    fi
    log "Infrastructure OK"
}

check_timezone() {
    HOUR=$(TZ='Asia/Shanghai' date +%H)
    if [ "$HOUR" -lt 5 ] && [ "$HOUR" -ge 0 ]; then
        log "WARNING: Running before 05:00 Beijing time. US market may still be open."
        log "Consider waiting until after 05:00 for complete data."
    fi
}

run_backfill() {
    log "=== Step 1: Backfill forward tracking ==="
    step_state "1_backfill" started
    cd "$PROJECT_DIR"
    python3 scripts/backfill_forward_tracking.py --db 2>&1 | tee -a "$LOG_FILE"
    step_state "1_backfill" completed
    log "Backfill complete"
}

run_scoreboard() {
    log "=== Step 2: Lifecycle scoreboard ==="
    step_state "2_scoreboard" started
    cd "$PROJECT_DIR"
    python3 scripts/lifecycle_scoreboard.py --db 2>&1 | tee -a "$LOG_FILE"
    step_state "2_scoreboard" completed
    log "Scoreboard complete"
}

run_tickets() {
    log "=== Step 3: Generate tickets ==="
    step_state "3_tickets" started
    cd "$PROJECT_DIR"
    python3 scripts/us_profit_ticket_pipeline.py --save-db --top-k 3 2>&1 | tee -a "$LOG_FILE"
    step_state "3_tickets" completed
    log "Tickets complete"
}

run_factor_optimization() {
    log "=== Step 4: Factor weight optimization ==="
    cd "$PROJECT_DIR"
    python3 scripts/weight_optimizer.py 2>&1 | tee -a "$LOG_FILE"
    log "Factor optimization complete"
}

run_signal_effectiveness() {
    log "=== Step 5: Signal effectiveness analysis ==="
    cd "$PROJECT_DIR"
    python3 scripts/signal_effectiveness.py --db 2>&1 | tee -a "$LOG_FILE"
    log "Signal effectiveness complete"
}

run_knowledge_export() {
    log "=== Step 6: Knowledge asset export ==="
    cd "$PROJECT_DIR"
    python3 scripts/knowledge_asset_export.py --date "$DATE" 2>&1 | tee -a "$LOG_FILE"
    log "Knowledge export complete"
}

run_obsidian_sync() {
    log "=== Step 7: Obsidian sync ==="
    cd "$PROJECT_DIR"
    python3 scripts/obsidian/sync_obsidian.py 2>&1 | tee -a "$LOG_FILE"
    log "Obsidian sync complete"
}

run_vector_update() {
    log "=== Step 8: Vector embedding update ==="
    cd "$PROJECT_DIR"
    python3 scripts/obsidian/generate_embeddings.py 2>&1 | tee -a "$LOG_FILE"
    log "Vector update complete"
}

show_results() {
    log "=== Pipeline Results ==="
    psql "$DATABASE_URL" -c "
        SELECT symbol, ticket_score, market_score, classification
        FROM tickets
        WHERE output_date = '$DATE'
        ORDER BY ticket_score DESC
        LIMIT 5;
    " 2>&1 | tee -a "$LOG_FILE"
}

# Parse arguments
MODE="full"
while [[ $# -gt 0 ]]; do
    case $1 in
        --backfill) MODE="backfill"; shift ;;
        --tickets) MODE="tickets"; shift ;;
        --knowledge) MODE="knowledge"; shift ;;
        --help) echo "Usage: $0 [--backfill|--tickets|--knowledge]"; exit 0 ;;
        *) shift ;;
    esac
done

# Main execution
acquire_lock
log "=========================================="
log "xiaomei daily pipeline starting"
log "Mode: $MODE"
log "Date: $DATE"
log "Run: $RUN_ID"
log "=========================================="

check_services
check_timezone

case $MODE in
    full)
        run_backfill
        run_scoreboard
        run_tickets
        run_factor_optimization
        run_signal_effectiveness
        run_knowledge_export
        run_obsidian_sync
        run_vector_update
        show_results
        ;;
    backfill)
        run_backfill
        run_scoreboard
        ;;
    tickets)
        run_tickets
        run_knowledge_export
        show_results
        ;;
    knowledge)
        run_knowledge_export
        run_obsidian_sync
        run_vector_update
        ;;
esac

log "=========================================="
log "xiaomei daily pipeline complete"
log "=========================================="
