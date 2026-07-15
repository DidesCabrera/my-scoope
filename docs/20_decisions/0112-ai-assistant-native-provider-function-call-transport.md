# 0112 · AI Assistant native provider function-call transport

Status: accepted
Date: 2026-07-13
Scope: OpenAI Responses adapter, tool orchestration, stateless continuation, CM24 live validation

## Context

The third CM24 live run proved that strict Structured Outputs improved simple text turns but did not make nested textual tool transport reliable. Operational scenarios still produced parse failures, truncated structural fragments and missing state updates.

The remaining weakness was architectural: My Scoope asked the provider to serialize tool names and JSON-string arguments inside the same assistant-authored envelope used for visible text. That duplicated the tool schemas, consumed output budget and treated operations as text instead of provider-native actions.

This is not a reason to restore deterministic intake parsing or add a more rigid questionnaire prompt.

## Decision

Use provider-native custom function calling for every AI Assistant operation exposed to OpenAI.

The provider request carries the allowlisted My Scoope function declarations separately from the prompt. OpenAI may return `function_call` output items. My Scoope maps those calls to `AssistantToolRequest`, performs its existing validation and permission checks, executes the controlled service, then returns one `function_call_output` for each call.

The follow-up provider request includes:

```text
original bounded messages
provider continuation output items
function_call_output items produced by My Scoope
```

The small `ai_assistant_structured_response.v2` JSON Schema remains, but only for:

```text
assistant_message
semantic intent
requires_human_review
```

Tool plans, tool names and tool arguments no longer travel inside that text envelope.

## Stateless reasoning continuity

The adapter continues to use `store=false`.

For GPT-5 reasoning/tool loops, the OpenAI adapter requests encrypted reasoning content and returns the bounded provider output items on the next call. Raw provider output is not exposed to the chat surface or persisted as conversation content.

Only explicit fields needed for continuation are forwarded. My Scoope tool results remain sanitized before becoming `function_call_output` payloads.

## Validation and permissions

Provider-native calling does not grant authority to the provider.

My Scoope remains responsible for:

- allowlisting tool names;
- validating arguments against internal contracts;
- enforcing authentication and object permissions;
- separating draft mutations from persistent writes;
- requiring approval for profile commits and reviewable proposals;
- limiting tool calls and loop iterations locally;
- rendering cards from controlled tool results.

The current dynamic draft-shaped function schemas use the existing server-side validator as the canonical boundary. Provider strictness may be enabled per function when its schema can satisfy the strict subset without weakening the product contract.

## Limits and repair

The local request estimator now includes function declarations, provider continuation items and function outputs. Function schemas therefore cannot bypass input limits merely because they are outside prompt text.

My Scoope enforces the maximum number of custom function requests locally. It does not rely on the provider `max_tool_calls` option for this boundary.

One bounded contract-repair call remains available for:

- malformed or incomplete final visible-text envelopes;
- an operational initial response that fails to emit the required native function call.

The repair does not invoke regex extraction, local semantic parsing or the deterministic intake engine.

## Observability

Safe metadata now records:

```text
provider_native_tool_transport
provider_native_tool_calls
provider_text_parse_ignored_due_to_native_tools
```

CM24 validates that any reported tool result came from native function-call transport. The final visible response must still pass the structured text boundary and must not be truncated.

## Consequences

- Operational actions no longer compete with visible text for one nested JSON output budget.
- Tool arguments are transported through the provider's function-call channel instead of an assistant-authored JSON string.
- My Scoope remains the execution and validation authority.
- Stateless GPT-5 tool loops preserve the provider continuation items required for coherent follow-up.
- Existing fake-provider textual tool envelopes remain accepted temporarily for backwards-compatible deterministic tests, but the OpenAI path uses native function calls.
- Decision 0111 remains historical evidence for the failed intermediate design and is superseded for tool transport by this decision.
- A fourth live CM24 run is required before the alignment extension can close.
