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

DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/pipeline-$DATE.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
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
    cd "$PROJECT_DIR"
    python3 scripts/backfill_forward_tracking.py --db 2>&1 | tee -a "$LOG_FILE"
    log "Backfill complete"
}

run_scoreboard() {
    log "=== Step 2: Lifecycle scoreboard ==="
    cd "$PROJECT_DIR"
    python3 scripts/lifecycle_scoreboard.py --db 2>&1 | tee -a "$LOG_FILE"
    log "Scoreboard complete"
}

run_tickets() {
    log "=== Step 3: Generate tickets ==="
    cd "$PROJECT_DIR"
    python3 scripts/us_profit_ticket_pipeline.py --save-db --top-k 3 2>&1 | tee -a "$LOG_FILE"
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
    PGPASSWORD=xiaomei2026 psql -h localhost -p 5432 -U xiaomei -d xiaomei -c "
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
log "=========================================="
log "xiaomei daily pipeline starting"
log "Mode: $MODE"
log "Date: $DATE"
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
