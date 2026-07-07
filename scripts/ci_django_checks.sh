#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-miapp.settings.dev}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export NUTRITION_ONBOARDING_GATE_ENABLED="${NUTRITION_ONBOARDING_GATE_ENABLED:-false}"
# CI runs the full historical suite in one process. Keep product rate limits
# configurable, but avoid test-order dependent 403s from django-ratelimit cache.
export RATE_LIMIT_AI_ASSISTANT_TURN_USER="${RATE_LIMIT_AI_ASSISTANT_TURN_USER:-10000/h}"
export RATE_LIMIT_AI_ASSISTANT_TURN_IP="${RATE_LIMIT_AI_ASSISTANT_TURN_IP:-10000/h}"

python manage.py check
python manage.py test
