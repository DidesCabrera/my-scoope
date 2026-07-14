# 0104 — AI Assistant draft update and card sharing boundary

Status: accepted
Date: 2026-07-13
Scope: `ai_assistant`, `notas`, LLM tool contracts and nutrition chat UI

## Context

The tool-oriented assistant baseline correctly separated temporary draft state from persistent user memory, but the first implementation coupled two different product actions:

```text
update_profile_draft
  -> update conversation state
  -> also return a new profile card
  -> chat renders the card automatically
```

The same pattern existed for preference and proposal-preference drafts.

This made every captured fact a presentation event. When the user supplied age, sex and activity in separate turns, the chat could render a new version of the same card after each answer. The result was visually repetitive and made the assistant feel like a rigid form even though the LLM was supposed to lead the conversation naturally.

A second inconsistency existed in `NutritionBrief.field_sources`: profile provenance survived session serialization, while sources for proposal and preference fields could be discarded because the cleaning boundary only admitted profile fields.

## Decision

Draft mutation and object presentation are separate capabilities.

```text
update_* draft tool
  -> validate typed values
  -> update conversation-scoped state
  -> return the structured draft
  -> no automatic card

share_*_card tool
  -> receive the current draft
  -> return a renderable product object
  -> chat may append the card
```

The accepted card-producing boundaries are:

```text
read_user_profile_context          -> initial profile card when the ficha is requested
share_profile_draft_card           -> deliberate profile review/completion card
share_preference_draft_card        -> deliberate preference review card
share_proposal_preferences_card    -> deliberate proposal-direction review card
```

Update tool results must remain useful to the provider and state synchronizer, but they are silent UI updates. The LLM may choose to call a share tool when the user asks to review an object, when an initial object should be visible, or after a meaningful grouped completion. It should not share a new card after every individual fact.

The backend must enforce this boundary by accepting cards only from explicit card-producing tools. A legacy or malformed update result containing a card payload must not make that card visible.

For provenance, each draft object keeps its own local `field_sources` map. After synchronization into `NutritionBrief`, provenance is stored in one flat canonical map keyed by the final brief field name:

```text
profile_draft.height_cm                 -> NutritionBrief.field_sources["height_cm"]
proposal_preferences.goal               -> NutritionBrief.field_sources["goal"]
preference_draft.avoided_foods          -> NutritionBrief.field_sources["excluded_foods"]
preference_draft.simplicity_preference  -> NutritionBrief.field_sources["style_preferences"]
```

This map must survive serialization and conversation round-trips for profile, proposal and preference fields.

## Consequences

- Partial answers update state without flooding the chat with intermediate cards.
- The initial ficha card remains visible when the user asks to use their profile.
- A completed or reviewable card is shown only through a deliberate share action.
- Tool descriptions, rather than rigid prompt sequencing, communicate when presentation is useful.
- The chat renderer has an allowlisted card-producer boundary independent of provider behavior.
- `NutritionBrief.field_sources` remains one canonical structure instead of introducing parallel profile/proposal/preference source maps.
- Proposal and preference provenance is retained between turns and can support future audit, labels and approval UX.

## Non-goals

This decision does not yet remove the remaining deterministic completeness policy, fixed conversational order or duplicated prompt rules. Those are separate follow-up patches so their behavioral effect can be tested independently.
