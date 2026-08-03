#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

if ! "${PYTHON_BIN}" -c "import coverage" >/dev/null 2>&1; then
  echo "Coverage is missing." >&2
  echo "Install it with: ${PYTHON_BIN} -m pip install -r requirements-quality.txt" >&2
  exit 2
fi

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-miapp.settings.dev}"
export NUTRITION_ONBOARDING_GATE_ENABLED="${NUTRITION_ONBOARDING_GATE_ENABLED:-false}"
export RATE_LIMIT_AI_ASSISTANT_TURN_USER="${RATE_LIMIT_AI_ASSISTANT_TURN_USER:-10000/h}"
export RATE_LIMIT_AI_ASSISTANT_TURN_IP="${RATE_LIMIT_AI_ASSISTANT_TURN_IP:-10000/h}"

"${PYTHON_BIN}" -m coverage run manage.py test "$@"
"${PYTHON_BIN}" -m coverage report
