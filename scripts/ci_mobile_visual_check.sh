#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

changed_mobile_files=()
while IFS= read -r file; do
  changed_mobile_files+=("$file")
done < <(
  {
    git diff --name-only --diff-filter=ACMR HEAD -- 'mobile/**/*.ts' 'mobile/**/*.tsx'
    git ls-files --others --exclude-standard -- 'mobile/**/*.ts' 'mobile/**/*.tsx'
  } | sort -u
)

echo "Running the visual iteration check on changed mobile files only."

if ((${#changed_mobile_files[@]})); then
  relative_files=()
  for file in "${changed_mobile_files[@]}"; do
    relative_files+=("${file#mobile/}")
  done
  (
    cd mobile
    npx eslint --no-cache "${relative_files[@]}"
  )
else
  echo "No changed mobile TypeScript files to lint."
fi

if (($#)); then
  (
    cd mobile
    npx tsx --test "$@"
  )
else
  echo "No focused test supplied; skipping tests during visual iteration."
fi
