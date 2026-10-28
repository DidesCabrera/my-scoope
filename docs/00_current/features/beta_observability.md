# Beta observability and incident coordination

Status: current
Date: 2026-10-28
Audience: developers, release operators, support and AI assistants

## Purpose

My Scoope correlates beta and production evidence without turning any single
provider into a complete health authority. The Observability Lead role coordinates
signals and routes work; it is not a daemon, deployment controller or replacement
for product specialists.

```text
tester symptom or automated signal
  -> build, release, environment and timestamp
  -> client plus server correlation
  -> one normalized incident
  -> severity and owner
  -> focused verification at the affected boundary
```

## Evidence sources

| Source | Strongest evidence | Does not prove |
| --- | --- | --- |
| TestFlight / App Store Connect | installed build, tester feedback and native crash reports | current repository code or server health |
| Expo / EAS | build artifact, profile, runtime/version and submission context | successful user journey after installation |
| Mobile Sentry | sanitized JS/native errors, traces, release/build/environment tags and safe breadcrumbs | absence of crashes when the installed build predates instrumentation |
| Backend Sentry | Django exceptions, performance signals and sanitized request context | complete Render process/deploy state |
| Render | deploys, process logs, restarts, memory and HTTP service evidence | client-side behavior without a correlated request |
| Repository | implementation, migrations, regression tests and release configuration | that a commit is deployed or installed |

Use request/support identifiers, route, timestamp, build and environment to correlate
sources. Never copy health, authentication, billing or nutrition payloads into an
incident record.

## Severity and routing

- **P0:** privacy/security, billing integrity, data loss or broad blocker.
- **P1:** crash or core journey failure without a practical workaround.
- **P2:** functional/navigation failure with a workaround, deployment drift or
  significant performance degradation.
- **P3:** comprehension, copy, content, portion guidance or visual defect unless
  impact raises its severity.

Route native runtime, React Native and navigation to mobile; Django/API/database to
backend; EAS/TestFlight/credentials/source maps to release; comprehension and flow to
UX/product. Verification is a distinct responsibility when closure requires evidence
outside the implementation boundary.

## Current instrumentation contract

- Backend and mobile Sentry disable default PII and sanitize sensitive keys, request
  bodies, provider payloads and user content.
- Mobile events carry application version, native build and deployment environment.
- Wheel-picker breadcrumbs record only surface and lifecycle (`open`, `commit`,
  `cancel`), never the selected value.
- Release builds need source-map/symbol upload credentials; local development builds
  deliberately do not depend on them.
- Render workers wait for the schema migrations known by their release before
  consuming jobs, preventing a worker from racing ahead of database deployment.
- Expected commercial limits must return controlled product errors instead of
  polluting incident monitoring as internal exceptions.
- High-value mobile reads use query budgets to turn observed N+1 regressions into
  executable evidence.

## Verification boundaries

A focused unit or integration test can prove the local fix. It cannot prove that:

- Render deployed that commit;
- a new mobile artifact contains it;
- TestFlight distributed the new build;
- source maps and symbols are accepted;
- a physical-device crash stopped recurring.

Close an incident only after the evidence layer that originally exposed it has been
rechecked, or record clearly why that external verification remains pending.

## Operational entrypoints

- `.codex/skills/observability-lead/SKILL.md`: reusable coordination procedure.
- `docs/40_technical/operations/ios_release_capabilities_runbook.md`: authoritative
  iOS build, TestFlight, Sentry and external-beta procedure.
- `python manage.py project_status --json`: sanitized environment and capability state.
- `python manage.py ai_project_context --json`: current project context for AI clients.
- `core/observability.py` and `mobile/src/observability/`: sanitization and SDK setup.

Live tools should be read-only unless the user explicitly authorizes the exact build,
deploy, environment, alert or tracker mutation.
