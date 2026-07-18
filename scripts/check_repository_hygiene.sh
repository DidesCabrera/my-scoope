#!/usr/bin/env bash
set -euo pipefail

forbidden_pattern='(^|/)(__pycache__/|\.env($|\.)|db\.sqlite3($|\.)|.*\.(orig|rej|pyc)$)'
tracked_offenders="$(git ls-files | grep -E "${forbidden_pattern}" | grep -v '^\.env\.example$' || true)"

if [[ -n "${tracked_offenders}" ]]; then
  echo "Repository hygiene check failed. Remove these local/generated artifacts from version control:" >&2
  echo "${tracked_offenders}" >&2
  exit 1
fi

while IFS= read -r tracked_report; do
  [[ -z "${tracked_report}" ]] && continue
  if ! grep -Fxq "${tracked_report}" scripts/legacy_root_artifacts.txt; then
    echo "Repository hygiene check failed. New root report must live under artifacts/local or reviewed docs archive: ${tracked_report}" >&2
    exit 1
  fi
done < <(git ls-files '*_report*.json')

echo "Repository hygiene check passed."
