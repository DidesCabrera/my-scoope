#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
MOBILE_ROOT="$REPOSITORY_ROOT/mobile"
PORT_START="${1:-8081}"
PORT_END="${2:-8090}"

if ! [[ "$PORT_START" =~ ^[0-9]+$ && "$PORT_END" =~ ^[0-9]+$ ]] || (( PORT_START > PORT_END )); then
  printf 'usage: %s [first-port] [last-port]\n' "$0" >&2
  exit 2
fi

printf 'repository_root=%s\n' "$REPOSITORY_ROOT"
printf 'mobile_root=%s\n' "$MOBILE_ROOT"
printf 'branch=%s\n' "$(git -C "$REPOSITORY_ROOT" branch --show-current)"
printf 'commit=%s\n' "$(git -C "$REPOSITORY_ROOT" rev-parse --short HEAD)"

if [[ -n "$(git -C "$REPOSITORY_ROOT" status --porcelain -- mobile)" ]]; then
  printf 'mobile_worktree=dirty\n'
else
  printf 'mobile_worktree=clean\n'
fi

if ! command -v lsof >/dev/null 2>&1; then
  printf 'metro_scan=unavailable_lsof\n'
  exit 0
fi

MATCHING_PORT=""
FREE_PORT=""
for (( PORT=PORT_START; PORT<=PORT_END; PORT++ )); do
  PIDS="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
  if [[ -z "$PIDS" ]]; then
    [[ -n "$FREE_PORT" ]] || FREE_PORT="$PORT"
    continue
  fi

  while IFS= read -r PID; do
    [[ -n "$PID" ]] || continue
    CWD="$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
    printf 'mobile_listener_port=%s pid=%s cwd=%s\n' "$PORT" "$PID" "${CWD:-unknown}"
    if [[ "$CWD" == "$MOBILE_ROOT" || "$CWD" == "$MOBILE_ROOT/"* ]]; then
      MATCHING_PORT="$PORT"
    fi
  done <<< "$PIDS"
done

if [[ -n "$MATCHING_PORT" ]]; then
  printf 'matching_metro_port=%s\n' "$MATCHING_PORT"
  printf 'recommended_action=reuse_matching_metro\n'
elif [[ -n "$FREE_PORT" ]]; then
  printf 'free_metro_port=%s\n' "$FREE_PORT"
  printf 'recommended_staging_command=npm run start:staging -- --port %s\n' "$FREE_PORT"
  printf 'recommended_local_command=npm run start:local -- --port %s\n' "$FREE_PORT"
else
  printf 'free_metro_port=none_in_range_%s_%s\n' "$PORT_START" "$PORT_END"
fi
