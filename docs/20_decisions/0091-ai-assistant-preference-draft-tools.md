# 0091 — AI Assistant preference draft tools

Status: accepted
Date: 2026-07-09
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0088-ai-assistant-profile-draft-tools.md`, `0090-ai-assistant-profile-commit-approval-tool.md`

## Context

The Client Memory cycle separated the user's body/profile data from food and meal preferences. The product discussion clarified that a good assistant should learn what matters to the user over time, but this memory must be visible, structured and controlled.

Profile draft tools already let the LLM complete body-related conversation state without writing to the persistent ficha. The next gap is preference memory: avoided foods, preferred foods, dietary pattern, allergies/intolerances and meal-organization preferences must not be mixed into the personal body profile.

## Decision

Add non-persistent preference draft tools to the AI Assistant tool registry:

```text
update_preference_draft
share_preference_draft_card
```

These tools are provider-exposed draft tools. They allow the LLM to interpret the user's natural-language preferences and write them into a bounded draft object for the current conversation.

They are deliberately separate from profile tools:

```text
profile_draft      -> body/profile calculation context
preference_draft   -> foods, restrictions and meal organization preferences
proposal_settings  -> proposal-specific parameters such as target and final meal count
```

The tools return a `preference_draft_card` payload that My Scoope can render in the chat thread as a product object, instead of relying on the LLM to describe memory in free text.

## Safety boundary

Preference draft tools do not persist data.

```text
writes_allowed = false
persistent_preferences_updated = false
persistence_requires_user_approval = true
```

A future commit tool may persist approved preference memory, but it must follow the same pattern as profile commits: trusted server-side approval from a UI action, not a provider-requested write.

## Consequences

- The LLM can act more like an assistant by completing preference memory through tools.
- The UI can show preferences as cards distinct from the personal ficha.
- `preferred_meals_per_day` is treated as meal-organization preference/proposal context, not as a body-profile field.
- The current patch does not create new persistent preference models or migrations.
- Future CM patches should connect approved preference memory to proposal generation and optimizer constraints.
