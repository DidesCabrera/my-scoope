#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/mobile"

echo "Running the fast mobile iteration gate (lint, types, and focused contract/unit suite)."
npm run lint -- --no-cache
npm run typecheck
npm test
