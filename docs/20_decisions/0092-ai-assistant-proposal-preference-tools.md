# 0092 — AI Assistant proposal preference tools

Status: accepted
Date: 2026-07-09
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0088-ai-assistant-profile-draft-tools.md`, `0091-ai-assistant-preference-draft-tools.md`

## Context

CM03–CM06 gave the assistant tool-backed objects for body/profile context and food/meal preference memory. The next boundary is proposal-scoped information: objective, meal count for the current proposal, energy adjustment and optional macro targets.

These fields are important for proposal creation, but they are not all persistent personal data. In particular, meal count and goal can change from one proposal to another. If they are stored inside the personal profile card, the UX suggests they are permanent ficha data and the assistant can ask or remember them in the wrong place.

## Decision

Add non-persistent proposal preference tools:

```text
update_proposal_preferences
share_proposal_preferences_card
```

These tools let the LLM act as an assistant by turning natural language into a bounded `proposal_preferences` object for the current work.

The object may include:

```text
goal
requested_entity
meals_per_day
energy_adjustment
calorie_target
protein_target
carb_target
fat_target
notes
```

The tool returns a `proposal_preferences_card` so the chat can show proposal parameters as a product object rather than embedding them in free text.

## Boundary

Proposal preferences are proposal-scoped.

```text
persistent_profile_updated = false
persistent_preferences_updated = false
proposal_scoped_only = true
writes_allowed = false
```

They may be used to assemble a future `NutritionBrief` for proposal creation, but they do not update the user's ficha or reusable food preference memory.

## Consequences

- The number of meals is no longer treated as a personal-profile field.
- Goal and macro targets can be represented as current-proposal parameters.
- The assistant can show a separate “Preferencias de propuesta” card.
- Future proposal creation tools should assemble `NutritionBrief` from three explicit objects: `profile_draft`, `preference_draft` and `proposal_preferences`.
- Persistent preference/profile updates continue to require their own approval tools.
