# 0097 · AI Assistant tool-led regression tests

Status: accepted
Date: 2026-07-10
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0094-ai-assistant-tool-result-state-sync.md`, `0096-ai-assistant-tool-oriented-intake-context.md`

## Context

The Client Memory & Profile Objects cycle moved the AI Assistant toward a tool-oriented operator model. The LLM can now complete profile drafts, preference drafts and proposal preferences through typed tools, and My Scoope can render those tool results as chat cards.

However, the most important UX failure to prevent is regression to the earlier pattern:

```text
The assistant says it understood a fact through a tool result,
but the visible next message asks for that same fact again.
```

This can happen if the provider returns visible text that contradicts tool-synchronized state. A pre-tool guard is not sufficient because the fact may only become known after tool execution.

## Decision

Add CM12 regression tests for tool-led memory and no-repeat behavior, and add a post-tool visible-text guard in the nutrition intake LLM adapter.

The guard runs after successful tool results are folded into the conversation-scoped `NutritionBrief`. If the provider-visible text asks for a fact that is now known because of those tool results, My Scoope replaces that text with a neutral acknowledgement and records metadata:

```text
llm_tool_state_visible_text_guarded = true
llm_preview_fallback_reason = asked_for_tool_synced_intake_facts
llm_production_fallback_reason = asked_for_tool_synced_intake_facts
```

The LLM remains the assistant/operator, but My Scoope prevents user-visible contradictions between tool state and chat text.

## Consequences

- Tool results remain the source for conversation-scoped draft memory.
- The UI should not show a question for a field that was captured in the same tool loop.
- Draft tools still do not persist profile or preference memory.
- Persistent updates continue to require explicit user approval.
- Regression tests now cover multi-object tool result synchronization across profile, preferences and proposal preferences.

## Non-goals

- This does not replace the provider with a deterministic interviewer.
- This does not persist preferences or profile updates automatically.
- This does not close the full cycle; CM13 should still document final state and remaining follow-ups.
