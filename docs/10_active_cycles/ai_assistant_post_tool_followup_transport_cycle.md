# AI Assistant Post-Tool Follow-up Transport Cycle

Status: completed
Date: 2026-07-14
Owner: Product / AI Assistant / Runtime
App targets: `ai_assistant`
Related areas: OpenAI Responses transport, native function-call loop, post-tool fallback, real-provider UX gate, test doubles
Predecessor: `ai_assistant_behavioral_alignment_cycle.md` (BA00–BA07)

## Context

The behavioral alignment cycle (BA02–BA05) treated the assistant's empty and
repetitive replies as an LLM behavior problem and iterated on prompts, tool
governance, agency and response style. Real transcripts kept showing something
more basic was broken, while fake-provider tests stayed green.

Direct code and report inspection identified a different, dominant cause:

```text
On essentially every tool-using turn, the post-tool follow-up call to the
provider fails. My Scoope then falls back to the deterministic local
acknowledgement (_local_acknowledgement_from_tool_results). The assistant
almost never words its own post-tool reply, so the user sees canned state
phrases such as "La información solicitada quedó disponible."
```

### Evidence

```text
- cm24_real_provider_report_after_state_only_local_ack.json:
  post_tool_fallback = {local_ack: true, provider_followup_failed: true}
  on 100% of tool turns; the FIRST provider call was healthy.
- Decision 0117 already noted it: "the provider failed only on the post-tool
  wording request", but treated it as a secondary degradation.
- Live transcript replies are verbatim matches of the hardcoded fallback
  strings in orchestrator.py (update_proposal_preferences -> "La dirección de
  la propuesta quedó actualizada."; read_* -> "La información solicitada quedó
  disponible.").
```

### Why it stayed invisible for three cycles

```text
- The OpenAI client discarded the API error body (only kept the status code),
  so the one message naming the defect was thrown away on every failure.
- The provider_followup_failed telemetry was only added in the last cycle, so
  earlier failures were absorbed silently and misread as passive/repetitive LLM
  behavior.
- The unit-test double (FakeLLMClient) ignores continuation_items, tool_outputs,
  call_id correlation, reasoning items and encrypted_content, and returns canned
  text for any request. Tool-loop tests assert the orchestrator BUILT a
  well-shaped tool_output, never that the real Responses API would ACCEPT the
  request. The contract mismatch is un-catchable by the suite as written.
```

## Product thesis

```text
Make provider failures loud and attributable, then fix the transport.
Never let a resilience fallback silently mask a systematic failure.
```

The likely transport defect lives in the follow-up request, which combines in
one call: `store=false` + reasoning replay (`include: reasoning.encrypted_content`),
strict structured output (`response_schema_strict` always true), and the full
tool catalog (`max_tool_loop_iterations=3` leaves `remaining>0`). The exact
cause is one JSON error message away — which the client used to discard.

## Non-goals

This cycle does not:

- change the user-visible, state-only local acknowledgement wording;
- alter tool governance, permissions, drafts, cards or approval boundaries;
- introduce a deterministic conversation planner or backend semantic parser;
- undo the behavioral work in BA02–BA05 (those requirements still hold; they
  were merely un-validatable while the ack overwrote model output).

## Work plan

### PT00 — Cycle registration and scope — completed

- Register the transport cycle, its root cause and its evidence.
- Record that BA02–BA05 addressed symptoms the fallback was generating or
  hiding, and that behavioral validation resumes only once the follow-up works.
- Define scope, non-goals, stages and closure evidence.

### PT01 — Preserve and read the provider error (unblocker) — delivered in this patch

- Enrich `LLMProviderRequestError` with bounded structured detail: HTTP status,
  provider `type`/`code`, `param` and `x-request-id`.
- Stop discarding the OpenAI 4xx/5xx body; parse it, preserve it on the error
  and log it server-side (never the API key, only a bounded slice).
- Surface the detail into turn metadata on the post-tool follow-up failure path
  (audit/observability), without changing the user-visible acknowledgement.
- Validation: `ai_assistant/tests/test_provider_error_capture.py` (offline; a
  stubbed 4xx/5xx response yields a fully populated error).

### PT02 — Reproduce the one-tool follow-up against the real provider — corrected

The first PT02 probe was useful but not contract-faithful enough to close the
transport diagnosis:

- it used a reduced prompt, response schema and one synthetic tool instead of
  `ExternalLLMOrchestrator.build_provider_request()` and
  `build_tool_followup_provider_request()`;
- `--no-strict` accidentally removed the schema and activated the
  `json_object` fallback, producing its own 400 because the reduced prompt did
  not mention JSON;
- `--no-reasoning` removed only `reasoning_effort` but still replayed encrypted
  reasoning items, so it did not isolate reasoning replay;
- `--show-payload` printed an indicative structure, not the exact payload built
  by the OpenAI adapter.

PT02 now uses the production orchestrator builders, the full prompt/schema/tool
catalog and the same `build_openai_responses_payload()` helper used by the HTTP
client. The toggles modify only the dimension they name, and missing `call_id`
is treated as a diagnostic failure instead of being synthesized.

A green minimal or exact probe does not by itself close PT03. The original live
scenario must also be re-run because product context and controlled tool output
shape can still expose a route-specific defect.


### PT01F — Diagnostic propagation and release gate — completed

- Forward bounded provider follow-up detail through the chat-engine metadata so
  the real-provider report contains status, type, code, message, param and
  `x-request-id` for the exact rejected request.
- Persist only stable identifiers (not the provider message) in
  `AIUsageEvent.metadata` to avoid long-lived storage of text that a provider
  error could echo from the request.
- Add a hard `provider_followup_health` gate: any healthy tool turn with
  `provider_tool_followup_failed=true` fails the real-provider validation.
- Update the local-ack pacing contract to the current `state_ack_only.v2`.

### PT03 — Preserve opaque call IDs and validate correlation — completed

The contract-faithful live probe isolated the same provider error under all
transport variants:

```text
No tool output found for function call call_NdjKFTviYMyNJVQnXNGgvNuv.
```

The defect was local and deterministic. `AssistantToolRequest` and
`AssistantToolResult` passed `request_id` through `_normalize_identifier()`,
which lowercased provider IDs. OpenAI emitted (for example)
`call_NdjKFTviYMyNJVQnXNGgvNuv`, while My Scoope returned the tool result as
`call_ndjkftviymynjvqnxnggvnuv`. Responses API `call_id` values are opaque and
case-sensitive, so the function call had no matching output.

PT03 therefore:

- preserves provider correlation IDs exactly, trimming only outer whitespace;
- keeps semantic identifier normalization only for My Scoope-owned names such
  as tool names and error codes;
- validates a one-to-one, case-sensitive mapping between every replayed
  `function_call` and `function_call_output` before sending HTTP;
- fails locally with a precise transport error for missing, duplicate or
  unexpected outputs;
- adds regression coverage using mixed-case IDs copied from the live failure.

Tools, strict structured output and encrypted reasoning replay remain enabled;
the four live variants proved they were not the cause of this failure.

### PT04 — Make the failure loud, not silent — completed

- Post-tool local acknowledgements are persisted as `degraded`, never as healthy
  completed turns.
- Both provider failures and technical-limit acknowledgements fail the live
  release gate.
- Safe degradation metadata is available in usage events and logs.
- `check_post_tool_followup_health` provides an alertable non-zero exit status
  when recent degradations exceed the configured threshold.
- Usage reports count degraded events separately from completed, blocked and
  error turns.

### PT05 — Contract-faithful test double and real-provider assertion — completed

- The production Responses payload validates exact, case-sensitive function-call
  correlation and rejects replayed reasoning items that lack the encrypted
  content required by stateless (`store=false`) continuation.
- `FakeLLMClient` applies the same continuation validation before recording or
  answering a scripted request, so malformed post-tool requests fail offline.
- The real-provider gate requires `provider_followup_failed == false` on healthy
  tool turns and rejects local acknowledgement copy on a non-degraded tool turn.
- Regression coverage proves that both the real payload builder and the fake
  reject malformed reasoning/call correlation before provider I/O.

### PT06 — Re-validate the behavioral items the ack was masking — completed

- Added a targeted real-provider scenario that reads the personal ficha and
  treats every actually persisted peso/altura/edad/sexo fact as known in the
  same tool-led turn.
- Closed a gate blind spot: same-turn facts now fail if they reappear as semantic
  missing slots or as visible profile questions in provider-written copy.
- Re-ran the ambiguous-message restraint contract with the original wording
  `¿Qué está pasando?`; the scenario permits no reads, writes or cards.
- Kept visible-question detection scenario-owned and bounded, avoiding a global
  deterministic language parser.

#### PT06 corrective validation — completed

The first live run used a staging ficha with weight and height present but age
and sex genuinely absent. The assistant correctly named those fields as
pending, while the static fixture incorrectly treated them as already known.
The scenario now performs a profile preflight: available facts become exact
brief/stability requirements, missing facts remain valid follow-up candidates,
and the report exposes both sets through a diagnostic check.

## Invariants (added to the gate)

```text
- healthy tool turns are worded by the provider, not by the local ack;
- provider_followup_failed is ~0% on the real-provider gate;
- a systematic follow-up failure fails the release; it is never absorbed silently;
- the local acknowledgement remains state-only AND rare;
- known facts already visible in cards / ficha are not re-requested.
```

## Validation strategy

- PT01: `python manage.py test ai_assistant.tests.test_provider_error_capture` (offline).
- PT02: `python manage.py reproduce_post_tool_followup --live [--provider openai] [--show-payload]`
  to capture the exact 400, then re-run with `--no-strict` / `--no-tools` /
  `--no-reasoning` to isolate the culprit.
- PT03–PT06: chat-engine and replay tests, then targeted real-provider reports
  (`validate_ai_assistant_real_provider --live --scenario ficha_conocida_sin_repreguntas
  --scenario referencia_ambigua_sin_tools`).
- Full regression at cycle closure.

## Closure criteria

1. The exact follow-up error is captured and named (PT01–PT02).
2. The follow-up succeeds on real-provider tool turns; local ack frequency ~0 (PT03–PT04).
3. The test suite can catch a malformed continuation (PT05).
4. Live transcripts show natural post-tool replies, no canned acks (PT06 + human review).
5. Decision 0117 is re-scoped: the state-only ack survives, but only as a true rare fallback.

## Meta-note

The real-provider gate and the `provider_followup_failed` telemetry added in the
previous cycle were correct — they are what exposed this. The durable process
fix is to treat that field as a release-blocking metric and to keep provider
errors readable, so diagnosis never again depends on discarded evidence.
