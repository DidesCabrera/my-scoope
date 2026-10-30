#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "${PROJECT_ROOT}"

echo "Checking repository growth budgets before expensive validation..."
"${PYTHON_BIN}" scripts/check_frontend_debt.py
"${PYTHON_BIN}" scripts/check_backend_debt.py
node scripts/check_mobile_test_debt.mjs
echo "Repository growth-budget preflight passed."
