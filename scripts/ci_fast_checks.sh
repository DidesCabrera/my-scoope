#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-miapp.settings.dev}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export NUTRITION_ONBOARDING_GATE_ENABLED="${NUTRITION_ONBOARDING_GATE_ENABLED:-false}"
export RATE_LIMIT_AI_ASSISTANT_TURN_USER="${RATE_LIMIT_AI_ASSISTANT_TURN_USER:-10000/h}"
export RATE_LIMIT_AI_ASSISTANT_TURN_IP="${RATE_LIMIT_AI_ASSISTANT_TURN_IP:-10000/h}"

scripts/check_repository_hygiene.sh
"${PYTHON_BIN}" scripts/check_frontend_debt.py
"${PYTHON_BIN}" scripts/check_e2e_contract.py
"${PYTHON_BIN}" manage.py check
"${PYTHON_BIN}" manage.py makemigrations --check --dry-run
"${PYTHON_BIN}" manage.py document_registry --strict
"${PYTHON_BIN}" manage.py test \
  core.tests.regressions \
  core.tests.test_application_dependencies \
  notas.tests.test_architecture_boundaries \
  notas.tests.test_bounded_contexts \
  notas.tests.test_domain_model_boundaries \
  food_catalog.tests.test_boundary_contracts \
  nutrition_solver.tests.test_app_boundary \
  billing.tests.test_architecture
