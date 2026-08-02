#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

if ! "${PYTHON_BIN}" -c "import pytest, playwright" >/dev/null 2>&1; then
  echo "Browser test dependencies are missing." >&2
  echo "Install them with: ${PYTHON_BIN} -m pip install -r e2e/requirements.txt" >&2
  exit 2
fi

export MYSCOOPE_E2E_BASE_URL="${MYSCOOPE_E2E_BASE_URL:-http://127.0.0.1:8000}"
if [[ "$#" -eq 0 ]]; then
  set -- e2e
fi
"${PYTHON_BIN}" -m pytest "$@"
