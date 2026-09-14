#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLASSIFIER="$ROOT_DIR/scripts/ci_change_scope.sh"
PATH_FIXTURE="$(mktemp)"
trap 'rm -f "$PATH_FIXTURE"' EXIT

assert_tier() {
  expected="$1"
  shift
  printf '%s\n' "$@" > "$PATH_FIXTURE"
  actual="$(CI_CHANGED_PATHS_FILE="$PATH_FIXTURE" "$CLASSIFIER" ignored-base ignored-head)"
  if [[ "$actual" != "$expected" ]]; then
    echo "expected tier $expected, got $actual for: $*" >&2
    exit 1
  fi
}

assert_tier docs AGENTS.md docs/00_current/README.md
assert_tier mobile mobile/src/app/today.tsx mobile/tests/contracts.test.ts docs/00_current/api/mobile-v1.openapi.json
assert_tier mobile scripts/ci_mobile_iteration.sh
assert_tier staging-fast notas/application/services/example.py mobile/src/app/today.tsx
assert_tier full notas/migrations/0001_initial.py
assert_tier full accounts/views.py
assert_tier full billing/services.py
assert_tier full requirements.txt
assert_tier full mobile/package-lock.json
assert_tier full .github/workflows/django-ci.yml
assert_tier full scripts/ci_mobile_checks.sh

: > "$PATH_FIXTURE"
actual="$(CI_CHANGED_PATHS_FILE="$PATH_FIXTURE" "$CLASSIFIER" ignored-base ignored-head)"
if [[ "$actual" != "full" ]]; then
  echo "an empty change set must fail safe to full, got $actual" >&2
  exit 1
fi

echo "CI change-scope classification passed."
