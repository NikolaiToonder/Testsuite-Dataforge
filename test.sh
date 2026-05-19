#!/bin/bash

export NO_COLOR=1
export FORCE_COLOR=0
export CI=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

ERROR_LOG="$LOG_DIR/testsuite_log.txt"
ERROR_LOG_LINT="$LOG_DIR/lint_log.txt"
ERROR_LOG_VITEST="$LOG_DIR/vitest_log.txt"
ERROR_LOG_E2E="$LOG_DIR/e2e_log.txt"

time_step() {
    local name="$1"
    local logfile="$2"
    shift 2

    local start=$SECONDS

    echo ""
    echo "▶️ $name..."
    echo "--- $name START ($(date)) ---" >> "$logfile"

    "$@" >> "$logfile" 2>&1
    local status=$?

    local duration=$((SECONDS - start))

    echo "--- $name END ($(date)) ---" >> "$logfile"
    echo "--- Duration: ${duration}s ---" >> "$logfile"

    if [ $status -eq 0 ]; then
        echo "✅ $name succeeded after ${duration}s"
    else
        echo "❌ $name: Some of the tests failed after ${duration}s. See $logfile"
    fi

    return $status
}

echo "--- TEST- OG LINT-KJØRING ($(date)) ---" > "$ERROR_LOG_LINT"
echo "--- TEST RAMMEVERK-KJØRING ($(date)) ---" > "$ERROR_LOG"
echo "--- VITEST INTEGRASJONSTEST-KJØRING ($(date)) ---" > "$ERROR_LOG_VITEST"
echo "--- PLAYWRIGHT E2E-KJØRING ($(date)) ---" > "$ERROR_LOG_E2E"

time_step "Ruff linting" "$ERROR_LOG_LINT" \
    ruff check "$SCRIPT_DIR/../dataforge/backend/app" "$SCRIPT_DIR/../dataforge/backend/main.py" \
    --force-exclude \
    --output-format=concise \
    --no-cache \
    --color=never

time_step "Pytest" "$ERROR_LOG" \
    pytest -q --tb=short --no-header --disable-warnings --show-capture=no --color=no

time_step "Vitest" "$ERROR_LOG_VITEST" \
    bash -c "cd '$SCRIPT_DIR/frontend' && CI=true NO_COLOR=1 npm run test:integration -- --run --no-color"

time_step "Playwright" "$ERROR_LOG_E2E" \
    "$SCRIPT_DIR/run-e2e.sh"