# 0113 — Proposal complexity and post-tool provider resilience

Date: 2026-07-13
Status: accepted
Scope: proposal-preference draft, native function-call loop, CM24 live validation

## Context

The fourth CM24 live run validated the native OpenAI function-call transport in the operational scenarios: grouped facts produced five native calls and direction changes produced three. Two narrow gaps remained.

First, `complexity_level` already existed in `NutritionBrief` and readiness rules, but it was not accepted by `update_proposal_preferences`. A user phrase such as “algo simple” could therefore be understood in visible text without becoming durable proposal-scoped state.

Second, `read_proposal` successfully emitted and executed a native function call, but the provider request that should explain the typed `not_found` result failed. The runtime then discarded the useful tool evidence, marked the whole turn as failed and returned a generic provider message.

## Decision

### Proposal complexity belongs to proposal preferences

`update_proposal_preferences` accepts the canonical field:

```text
complexity_level = low | medium | high
```

The tool normalizes common user language such as `simple`, `intermedia` and `más elaborada`, synchronizes the value into `NutritionBrief` and displays it in the proposal-preferences card.

This is proposal-scoped state. It does not become persistent personal preference memory.

### A completed tool operation survives a follow-up provider failure

When all of the following are true:

1. the provider emitted a valid native function call;
2. My Scoope validated and executed the tool;
3. a typed result exists;
4. only the subsequent provider call that should word the result fails;

My Scoope may finish the turn with a small local acknowledgement derived strictly from the typed result.

The fallback must:

- preserve the native function-call and tool-result evidence;
- avoid inventing facts, recommendations, questions or state transitions;
- expose bounded degradation metadata;
- record the turn as completed with a diagnostic error type;
- never invoke the deterministic intake runtime.

For a missing proposal, the local response may state only that the proposal was not found or is not visible to the current account and that no change was made.

## Why this is not a second conversational brain

The fallback does not interpret the user's nutrition request or choose the next conversational step. It only translates an already validated typed result into safe copy when the provider cannot complete the post-tool wording call.

The LLM remains responsible for selecting tools and conducting the conversation. My Scoope remains responsible for validation, execution, permissions and safe degradation.

## Consequences

- “Algo simple” can satisfy the existing proposal-readiness field through a typed tool.
- A transient provider failure after `read_*` no longer erases a successful native call or its controlled result.
- CM24 can distinguish provider degradation from a missing tool call or broken transport.
- A fifth live report is required before closing CM24, followed by manual transcript disposition.
