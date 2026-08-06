#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}/mobile"

npm run lint -- --no-cache
npm run typecheck
npm test
npm run export:web
