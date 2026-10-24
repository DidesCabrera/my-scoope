#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
MOBILE_ROOT="$REPOSITORY_ROOT/mobile"
METRO_PORT="${1:-8081}"

printf 'repository_root=%s\n' "$REPOSITORY_ROOT"
printf 'mobile_root=%s\n' "$MOBILE_ROOT"
printf 'branch=%s\n' "$(git -C "$REPOSITORY_ROOT" branch --show-current)"
printf 'commit=%s\n' "$(git -C "$REPOSITORY_ROOT" rev-parse --short HEAD)"

if [[ -n "$(git -C "$REPOSITORY_ROOT" status --porcelain -- mobile)" ]]; then
  printf 'mobile_worktree=dirty\n'
else
  printf 'mobile_worktree=clean\n'
fi

printf 'metro_port=%s\n' "$METRO_PORT"
if ! command -v lsof >/dev/null 2>&1; then
  printf 'metro_status=unknown_lsof_unavailable\n'
  exit 0
fi

PIDS="$(lsof -nP -iTCP:"$METRO_PORT" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
if [[ -z "$PIDS" ]]; then
  printf 'metro_status=not_listening\n'
  exit 0
fi

printf 'metro_status=listening\n'
while IFS= read -r PID; do
  [[ -n "$PID" ]] || continue
  CWD="$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
  printf 'metro_pid=%s\n' "$PID"
  printf 'metro_cwd=%s\n' "${CWD:-unknown}"
  if [[ "$CWD" == "$MOBILE_ROOT" || "$CWD" == "$MOBILE_ROOT/"* ]]; then
    printf 'metro_matches_checkout=yes\n'
  else
    printf 'metro_matches_checkout=no\n'
  fi
done <<< "$PIDS"
