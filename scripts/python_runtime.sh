#!/usr/bin/env bash

# Resolve the project interpreter without requiring callers to activate a virtual
# environment. Callers must define PROJECT_ROOT before sourcing this file.
resolve_project_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if [[ ! -x "${PYTHON_BIN}" ]]; then
      echo "PYTHON_BIN is not executable: ${PYTHON_BIN}" >&2
      return 1
    fi
    printf '%s\n' "${PYTHON_BIN}"
    return 0
  fi

  if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    printf '%s\n' "${PROJECT_ROOT}/.venv/bin/python"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  echo "No Python interpreter found. Create .venv or set PYTHON_BIN." >&2
  return 1
}
