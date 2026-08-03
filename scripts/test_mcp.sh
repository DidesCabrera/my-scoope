#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

if ! "${PYTHON_BIN}" -c "import mcp, starlette, uvicorn" >/dev/null 2>&1; then
  echo "MCP test dependencies are missing." >&2
  echo "Install them with: ${PYTHON_BIN} -m pip install -r mcp_server/requirements.txt" >&2
  exit 2
fi

export PYTHONPATH="${PROJECT_ROOT}/mcp_server:${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m unittest discover -s mcp_server/tests -p 'test*.py'
