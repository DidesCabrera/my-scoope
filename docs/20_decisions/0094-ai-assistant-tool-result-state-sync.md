# 0094 · AI Assistant tool result state sync

Date: 2026-07-09
Status: accepted
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0088-ai-assistant-profile-draft-tools.md`, `0091-ai-assistant-preference-draft-tools.md`, `0092-ai-assistant-proposal-preference-tools.md`

## Context

CM03-CM08 exposed ficha, preference, proposal-preference and comparison capabilities as tools. Those tools can now return structured objects and renderable chat cards.

A remaining boundary issue is that a tool result can be visible in the chat as a card while the legacy `NutritionConversationState.result.brief` still lacks the same facts. If the next deterministic fallback or proposal readiness check reads only the legacy brief, the assistant may appear to remember something visually but ask for it again later.

## Decision

Successful draft tool results must be folded back into the nutrition chat state for the current conversation.

This sync is not a persistent profile/preference write. It only updates the conversation-scoped `NutritionBrief` so the existing intake/proposal surface can stay aligned with controlled tool outputs.

## Implementation boundary

Tool result state sync may consume controlled local tool outputs such as:

```text
profile_draft
preference_draft
proposal_preferences
nutrition_brief_patch
```

and update the conversation brief with supported temporary fields:

```text
weight_kg
height_cm
age_years
sex
activity_level
training_frequency
goal
requested_entity
meals_per_day
energy_adjustment
calorie_target
protein_target
carb_target
fat_target
excluded_foods
preferred_foods
style_preferences
complexity_level
budget_level
notes
```

## Non-goals

- Do not persist profile or preference data from this sync.
- Do not expose `commit_profile_update` to the provider LLM.
- Do not treat proposal meal count as a permanent ficha field.
- Do not make cards the only source of state; cards are UI renderings of tool/state objects.

## Rationale

The LLM should act as the assistant/operator and call product tools. My Scoope should validate the tool outputs, render cards and keep conversation state aligned with those outputs.

This prevents a mismatch where:

```text
The card says a field is captured,
but the next turn still asks for it.
```

## Consequences

- Draft tools now influence proposal readiness through the conversation brief.
- The assistant can complete multiple fields through tools and keep the legacy intake UI coherent.
- Persistent memory still requires explicit approval through dedicated commit tools.
- Future proposal creation can assemble inputs from synced tool outputs instead of only deterministic text extraction.
