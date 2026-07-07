#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-miapp.settings.dev}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

python manage.py check
python manage.py test
