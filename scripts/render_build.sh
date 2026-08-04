#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

python -m pip install --disable-pip-version-check -r requirements.txt
npm ci --ignore-scripts
npm run build
python manage.py collectstatic --noinput
python manage.py check
