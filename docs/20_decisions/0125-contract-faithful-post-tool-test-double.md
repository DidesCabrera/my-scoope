# 0125 — Contract-faithful post-tool test double

Status: accepted
Date: 2026-07-14
Cycle: PT05

## Context

The production OpenAI Responses transport uses stateless continuations with
`store=false`. A valid post-tool request must preserve opaque, case-sensitive
`call_id` correlation and replay provider reasoning items with their
`encrypted_content`.

The previous `FakeLLMClient` recorded any continuation and returned scripted
text. It therefore accepted requests that the real provider rejected, which let
a systematic post-tool failure remain invisible to offline tests.

## Decision

- Reuse the production continuation validator in the fake provider whenever the
  request contains native `function_call` or `reasoning` continuation items.
- Reject missing, duplicated, unexpected or case-rewritten function outputs
  before the fake records the request.
- Reject replayed reasoning items without encrypted content before provider I/O.
- Keep legacy JSON-text tool simulations supported: they are not native
  Responses continuations and must not be misclassified as such.
- Treat a known local acknowledgement phrase on a supposedly healthy tool turn
  as a hard real-provider gate failure.

## Consequences

The test double now fails on the same malformed native continuation shapes as
the production adapter. Offline tool-loop tests can catch correlation and
reasoning replay regressions before a live-provider run, while older non-native
test fixtures remain valid.

The local acknowledgement remains available only as an explicit degraded
fallback. It cannot silently pass as provider-written output in release
validation.
