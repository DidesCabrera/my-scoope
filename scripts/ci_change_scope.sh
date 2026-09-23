#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "usage: $0 <base-revision> <head-revision>" >&2
  exit 2
fi

base_revision="$1"
head_revision="$2"
tier=docs
changed_count=0

changed_paths() {
  if [[ -n "${CI_CHANGED_PATHS_FILE:-}" ]]; then
    cat "$CI_CHANGED_PATHS_FILE"
  else
    git diff --name-only --no-renames "$base_revision" "$head_revision"
  fi
}

while IFS= read -r changed_path; do
  [[ -z "$changed_path" ]] && continue
  changed_count=$((changed_count + 1))

  case "$changed_path" in
    notas/application/culinary_*|notas/application/ai_intake/culinary_program.py|notas/application/services/nutrition/culinary_validation.py|nutrition_solver/application/culinary_planner.py|notas/tests/test_culinary_program.py)
      # Culinary generation must exercise PostgreSQL application, not just SQLite.
      # Name/field limits and approval persistence are part of the safety contract.
      tier=full
      break
      ;;
    scripts/ci_mobile_iteration.sh)
      if [[ "$tier" == "docs" ]]; then
        tier=mobile
      fi
      ;;
    .github/*|*/migrations/*|accounts/*|billing/*|miapp/settings/*|mobile_api/auth*|mobile_api/routes/auth*|mobile_api/security*|*/models.py|*/models/*|requirements*.txt|*/requirements*.txt|package.json|package-lock.json|mobile/package.json|mobile/package-lock.json|mobile/app.json|mobile/app.config.*|mobile/eas.json|mobile/ios/*|Dockerfile*|render*.yaml|pyproject.toml|pytest.ini|scripts/ci_*.sh|scripts/quality_checks.sh)
      tier=full
      break
      ;;
    AGENTS.md|*.md|docs/*)
      ;;
    mobile/*)
      if [[ "$tier" == "docs" ]]; then
        tier=mobile
      fi
      ;;
    *)
      tier=staging-fast
      ;;
  esac
done < <(changed_paths)

if [[ "$changed_count" -eq 0 ]]; then
  tier=full
fi

echo "$tier"
