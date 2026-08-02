#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

if ! "${PYTHON_BIN}" -c "import ruff, pip_audit" >/dev/null 2>&1; then
  echo "Quality dependencies are missing." >&2
  echo "Install them with: ${PYTHON_BIN} -m pip install -r requirements-quality.txt" >&2
  exit 2
fi

"${PYTHON_BIN}" -m ruff check \
  accounts admin_analytics admin_operations ai_assistant billing core email_delivery \
  food_catalog miapp notas nutrition_solver mcp_server/myscoope_mcp \
  --no-cache
"${PYTHON_BIN}" -m pip_audit -r requirements.txt --progress-spinner off
