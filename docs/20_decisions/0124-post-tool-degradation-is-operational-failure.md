# 0124 — Post-tool degradation is an operational failure

Status: accepted
Date: 2026-07-14

## Decision

A successful tool execution followed by a local acknowledgement is not recorded
as a completed AI turn. It is recorded as `degraded` because the provider failed
to produce the user-facing completion or the follow-up exceeded a technical
limit.

The local acknowledgement remains available as a last-resort resilience path,
but it is release-blocking in the real-provider gate and alertable through
usage observability.

## Operational contract

- Healthy tool turn: `AIUsageEvent.status = completed` and provider-written text.
- Local post-tool acknowledgement: `AIUsageEvent.status = degraded`.
- Degraded events retain only safe operational metadata; prompts, arguments and
  provider payloads are not persisted.
- `check_post_tool_followup_health` exits non-zero when the recent degraded count
  exceeds the configured threshold.
- Any local acknowledgement fails the real-provider release gate, including a
  technical-limit fallback where the provider itself did not return an error.

## Consequences

Dashboards and reports must count degraded events separately from completed,
blocked and failed turns. Credits and token usage remain observable because the
provider calls and successful tool work still consumed resources.
