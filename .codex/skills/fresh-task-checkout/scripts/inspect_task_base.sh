#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
BASE_REF="${1:-origin/staging}"

if ! git -C "$REPOSITORY_ROOT" rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null; then
  printf 'base_status=missing\n'
  printf 'base_ref=%s\n' "$BASE_REF"
  exit 2
fi

CURRENT_BRANCH="$(git -C "$REPOSITORY_ROOT" branch --show-current)"
CURRENT_HEAD="$(git -C "$REPOSITORY_ROOT" rev-parse HEAD)"
BASE_SHA="$(git -C "$REPOSITORY_ROOT" rev-parse "$BASE_REF^{commit}")"
read -r HEAD_ONLY BASE_ONLY <<< "$(git -C "$REPOSITORY_ROOT" rev-list --left-right --count HEAD..."$BASE_REF")"

printf 'repository_root=%s\n' "$REPOSITORY_ROOT"
printf 'current_branch=%s\n' "${CURRENT_BRANCH:-detached}"
printf 'current_head=%s\n' "$CURRENT_HEAD"
if [[ -n "$(git -C "$REPOSITORY_ROOT" status --porcelain)" ]]; then
  printf 'current_worktree=dirty\n'
else
  printf 'current_worktree=clean\n'
fi
printf 'base_status=available\n'
printf 'base_ref=%s\n' "$BASE_REF"
printf 'base_sha=%s\n' "$BASE_SHA"
printf 'current_only_commits=%s\n' "$HEAD_ONLY"
printf 'base_only_commits=%s\n' "$BASE_ONLY"

if git -C "$REPOSITORY_ROOT" rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null \
  && git -C "$REPOSITORY_ROOT" rev-parse --verify --quiet 'origin/staging^{commit}' >/dev/null; then
  read -r MAIN_ONLY STAGING_ONLY <<< "$(git -C "$REPOSITORY_ROOT" rev-list --left-right --count origin/main...origin/staging)"
  printf 'main_only_commits=%s\n' "$MAIN_ONLY"
  printf 'staging_only_commits=%s\n' "$STAGING_ONLY"
  if [[ "$MAIN_ONLY" == "0" ]]; then
    printf 'staging_contains_main=yes\n'
  else
    printf 'staging_contains_main=no\n'
  fi
else
  printf 'staging_contains_main=unknown\n'
fi
