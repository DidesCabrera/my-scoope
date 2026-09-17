#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${PROJECT_ROOT}/scripts/python_runtime.sh"
PYTHON_BIN="$(resolve_project_python)"
cd "${PROJECT_ROOT}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-miapp.settings.dev}"
export NUTRITION_ONBOARDING_GATE_ENABLED="${NUTRITION_ONBOARDING_GATE_ENABLED:-false}"
export RATE_LIMIT_AI_ASSISTANT_TURN_USER="${RATE_LIMIT_AI_ASSISTANT_TURN_USER:-10000/h}"
export RATE_LIMIT_AI_ASSISTANT_TURN_IP="${RATE_LIMIT_AI_ASSISTANT_TURN_IP:-10000/h}"

"${PYTHON_BIN}" manage.py test \
  ai_assistant.tests.test_user_request_capability_catalog \
  ai_assistant.tests.test_tool_selection_workspace_patch \
  ai_assistant.tests.test_prepared_actions \
  ai_assistant.tests.test_read_only_tool_executor \
  ai_assistant.tests.test_context_builder \
  notas.tests.test_ai_workspace_query_tool \
  notas.tests.test_ai_workspace_library_coherence \
  notas.tests.test_solver_food_candidates_query \
  notas.tests.test_macro_target_policy \
  notas.tests.test_nutrition_engine_target_estimator \
  notas.tests.test_nutrition_solver_meal_proposal \
  notas.tests.test_ai_assistant_real_provider_validation \
  notas.tests.test_ai_assistant_evaluation_lab \
  --keepdb
