#!/usr/bin/env bash
set -euo pipefail

forbidden_pattern='(^|/)(__pycache__/|\.env($|\.)|db\.sqlite3($|\.)|.*\.(orig|rej|pyc)$)'
tracked_offenders="$(git ls-files | grep -E "${forbidden_pattern}" | grep -v '^\.env\.example$' || true)"

if [[ -n "${tracked_offenders}" ]]; then
  echo "Repository hygiene check failed. Remove these local/generated artifacts from version control:" >&2
  echo "${tracked_offenders}" >&2
  exit 1
fi

echo "Repository hygiene check passed."
