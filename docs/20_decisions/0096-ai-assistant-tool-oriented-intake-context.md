# 0096 · AI Assistant tool-oriented intake context

Status: accepted
Date: 2026-07-09
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0094-ai-assistant-tool-result-state-sync.md`, `0095-ai-assistant-proposal-from-drafts-tool.md`

## Context

CM02-CM10 introduced tool families for profile drafts, preference drafts, proposal preferences, comparisons and proposal creation from drafts.

After those patches, the remaining risk was not the absence of tools, but the provider-facing context. If the LLM receives only legacy intake hints and a plain `nutrition_brief`, it can continue behaving like a text chatbot or slot interviewer instead of operating My Scoope objects through tools.

The assistant should remain intelligent and user-facing. The system should not replace it with a rigid deterministic interviewer. However, the system must provide an environment where the LLM knows which product objects exist, which tools update those objects and which actions require approval.

## Decision

Provider context for `ai_nutrition_intake` must include an explicit `tool_oriented_intake` section.

This section describes:

```text
assistant_role
current_drafts
recommended_tool_sequence
rules for recording user facts through tools
```

The context mirrors the current conversation-scoped state into draft-shaped objects:

```text
profile_draft
preference_draft
proposal_preferences
```

The LLM remains the assistant/operator. It can interpret natural language and decide which tool to request. My Scoope validates tool inputs, syncs tool results back into conversation state, renders cards and persists only after explicit approval.

## Consequences

- The LLM is instructed to use `update_profile_draft`, `update_preference_draft` and `update_proposal_preferences` when the user gives relevant facts.
- The LLM should not merely say it understood a fact unless that fact is already in `current_drafts` or it requests the matching update tool in the same turn.
- Proposal creation availability now follows `AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS` in provider context instead of being hardcoded as disabled.
- The legacy deterministic intake can remain as fallback/state bridge, but the provider-facing operating model is now tool-oriented.
- Meals per day are explicitly kept out of `profile_draft`; they belong to proposal preferences or reusable meal-organization preference drafts.

## Non-goals

- This decision does not remove the existing deterministic intake flow.
- This decision does not persist preferences or profile changes automatically.
- This decision does not make proposal tools available unless the explicit reviewable proposal setting enables them.
