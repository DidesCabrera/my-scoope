# Decision 0160: repository quality surfaces are explicit and independently runnable

Date: 2026-08-02
Status: accepted
Cycle: TDG01-TDG02

## Context

The authoritative Django workflow passed a large regression suite, but it did not
execute the separately packaged MCP tests or declare the Playwright-style browser
runtime. This made a green workflow narrower than a green repository.

The local aggregate script also assumed an activated virtual environment and failed
from an otherwise valid terminal where `python` was not on `PATH`.

## Decision

Treat Django, MCP and browser automation as three explicit quality surfaces:

- `scripts/ci_fast_checks.sh` owns sub-five-minute structural feedback and selected
  architecture/regression contracts;
- `scripts/ci_django_full_suite.sh` owns the complete Django regression suite;
- `scripts/test_mcp.sh` owns MCP contract/protocol discovery under
  `mcp_server/requirements.txt`;
- `scripts/test_e2e.sh` owns browser execution under `e2e/requirements.txt`.

The aggregate `scripts/ci_django_checks.sh` remains the authoritative local Django
boundary and delegates to fast plus full scripts. GitHub Actions runs fast Django,
full Django and MCP as independent jobs. Browser automation remains an explicitly
manual surface until TDG07 removes historical fixed IDs, sleeps and persisted auth
assumptions.

All repository scripts resolve `.venv/bin/python`, an explicit `PYTHON_BIN`, or a
system interpreter without requiring manual activation.

## Consequences

- A missing MCP runtime fails with an actionable installation command.
- MCP receives clean-environment CI coverage without becoming a Django app.
- Browser dependencies do not enter production requirements.
- A fast green result never replaces the complete Django regression result.
