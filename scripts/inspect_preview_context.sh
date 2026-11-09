#!/usr/bin/env bash
set -euo pipefail

exec python3 "$(dirname "$0")/inspect_preview_context.py" "$@"
