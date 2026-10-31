#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"

PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

# Development settings announce themselves on stdout. Keep structured context
# output machine-readable without changing the interactive development posture.
if [[ "${1:-}" == "ai_project_context" && " $* " == *" --json "* ]]; then
  "${PYTHON_BIN}" manage.py "$@" | sed '1{/^🚀 RUNNING IN DEV MODE$/d;}'
  exit "${PIPESTATUS[0]}"
fi

exec "${PYTHON_BIN}" manage.py "$@"
