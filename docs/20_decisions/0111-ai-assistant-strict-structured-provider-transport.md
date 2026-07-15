# 0111 · AI Assistant strict structured provider transport

Status: superseded by decision 0112
Date: 2026-07-13
Scope: OpenAI Responses adapter, assistant envelope, tool grounding, CM24 live validation

## Context

The second CM24 live run confirmed that provider identity and usage observability were healthy, but exposed two remaining transport failures:

- some provider responses were truncated or malformed and reached the visible boundary as a single `{` or as the internal contract-error fallback;
- some valid text responses described an operational change without returning the typed `tool_requests` required to update My Scoope state.

The problem was not a need for a more deterministic conversation script. The provider was being asked through legacy JSON-object mode to produce a large free-form envelope, while tool contracts were described only inside prompt text.

## Decision

> Historical intermediate design. Decision 0112 replaces textual tool transport with provider-native function calling while retaining a small structured visible-text envelope.


Use provider-enforced Structured Outputs for the assistant envelope when the OpenAI Responses adapter is active.

The internal transport moves to `ai_assistant_structured_response.v2` and supplies a strict JSON Schema through the whitelisted provider request metadata. The schema fixes the shape of:

```text
assistant_message
intent
semantic slots encoded as slots_json
tool_plan
tool_requests with arguments_json
requires_human_review
```

Tool arguments remain provider-agnostic JSON strings at the transport boundary and are decoded into the existing typed `AssistantToolRequest` before server validation or execution.

The envelope includes `tool_plan.required`. It must be true when the turn requires a real read, draft update, card share or reviewable create. If the provider declares an operation but omits `tool_requests`, or if the response is malformed/incomplete, the orchestrator may perform one structured repair call. It must not run a local semantic extractor or the deterministic intake engine.

## Output budget and reasoning

The product-wide output limit remains 900 tokens to preserve existing credit, routing and technical-limit behavior.

CM24 live validation may use a bounded 1,400-token output budget and low reasoning effort because it is a controlled diagnostic run designed to capture full structured envelopes. This does not silently change ordinary product pricing or limits.

## Prompt simplification

Because the response shape is now enforced at the provider boundary, the developer prompt no longer duplicates the full response schema. Redundant server-enforced policy flags are removed. Prompt content remains focused on:

- current objects and history;
- allowed typed tools;
- the boundary between text and product operations;
- adaptive response quality.

This reduces input size and avoids undoing CM20/CM21 through transport-related prompt growth.

## Observability

Safe metadata records:

```text
provider_parse_error
provider_contract_repair_attempted
provider_incomplete_reasons
```

CM24 adds a hard `structured_provider_contract` invariant. A final malformed envelope, incomplete response or visibly truncated `{` fails the gate. A successful one-time repair is diagnostic evidence, not automatically a failure.

## Consequences

- OpenAI enforces the envelope structure instead of relying only on prompt wording.
- The model retains freedom over tone, question order and conversational pacing.
- Operational facts still enter My Scoope only through typed tools.
- One repair retry improves resilience without creating an unbounded provider loop.
- Product-wide output and credit assumptions remain unchanged.
- A third live CM24 run is required before closing the alignment extension.
