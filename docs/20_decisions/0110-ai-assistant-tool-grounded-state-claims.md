# 0110 · AI Assistant tool-grounded state claims and live evidence calibration

Status: accepted
Date: 2026-07-13
Scope: AI Assistant runtime, tool contracts, CM24 real-provider validation

## Context

The first CM24 live run reached the configured OpenAI model and persisted one completed `AIUsageEvent` for every synthetic turn. However, the report mixed two different problems:

- provider/model/usage metadata was not forwarded by `ExternalLLMChatEngine`, so healthy provider calls were classified as missing or fallback turns;
- the model sometimes acknowledged profile/proposal facts in visible text without requesting the typed tools that make those facts part of My Scoope state.

The second issue is a real product regression. Natural language is not a write boundary. Saying “I will use these values” or “I changed the goal” must not create a second, text-only state that diverges from `NutritionBrief`, drafts and cards.

## Decision

Keep conversational freedom, but make operational claims tool-grounded:

```text
visible text explains the work
+ typed tools read or mutate temporary My Scoope objects
+ tool results are the source of truth
```

The provider contract now states explicitly:

- plain text never mutates My Scoope state;
- claims that a fact was registered, changed, read or will be used require the matching allowlisted tool request in that turn;
- explicit requests to read an entity or show a card require the corresponding tool;
- the model must not claim that tools are unavailable when the requested capability is present in `allowed_tools`.

This is not a conversation script. It does not prescribe question order, wording or number of questions. It defines the boundary between language and product operations.

## Live evidence

`AIUsageEvent` is the authoritative hard evidence that a provider turn occurred and was recorded. Safe chat metadata remains useful for diagnostics, and the adapter now forwards provider, model and usage summary, but missing adapter metadata alone must not invalidate a completed persisted event.

The CM24 validator therefore:

- rejects real technical fallbacks;
- accepts provider identity from either safe turn metadata or a completed non-fake usage event for the same turn;
- requires one completed usage event per synthetic user turn;
- detects text that claims tools are unavailable after a tool result was actually returned;
- explicitly requires share tools when a scenario asks to see cards.

## Consequences

- A natural response can still answer, explain or ask questions freely.
- Facts and direction changes cannot exist only in prose.
- Cards remain first-class objects rendered from tool results, not markdown substitutes.
- Provider health and cost evidence no longer depend on one metadata bridge.
- The first live CM24 report is evidence for this correction, not evidence that the alignment cycle has passed. A second live run is required.
