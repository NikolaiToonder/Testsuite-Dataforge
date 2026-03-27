#!/bin/bash

# Definer filer for output
ERROR_LOG="testsuite_log.txt"
ERROR_LOG_LINT="lint_log.txt"
echo "--- TEST- OG LINT-KJØRING ($(date)) ---" > $ERROR_LOG_LINT
echo "--- TEST RAMMEVERK-KJØRING ($(date)) ---" > $ERROR_LOG
echo "1. Kjører linter (Ruff)..."

ruff check ../dataforge >> $ERROR_LOG_LINT 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Linting ok."
else
    echo "❌ Linting feilet. Sjekk $ERROR_LOG."
fi

echo "2. Kjører Pytest..."

# --tb=short: Kompakt feilmelding
# -q: Quiet mode (viser bare det viktigste)
# --no-header: Fjerner systeminfo som KI-en ikke trenger

pytest -q --tb=short --no-header --disable-warnings --show-capture=no >> $ERROR_LOG 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Alle tester bestått!"
else
    echo "❌ Noen tester feilet. Feilmeldinger er lagret i $ERROR_LOG."
fi