# 0095 — AI Assistant proposal generation from draft objects

Date: 2026-07-09
Status: accepted
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0088-ai-assistant-profile-draft-tools.md`, `0091-ai-assistant-preference-draft-tools.md`, `0092-ai-assistant-proposal-preference-tools.md`, `0094-ai-assistant-tool-result-state-sync.md`

## Context

CM02–CM09 moved the Assistant toward a tool-oriented architecture:

```text
profile_draft
preference_draft
proposal_preferences
```

These objects let the LLM act as an assistant that interprets the user and fills structured product objects. However, proposal creation still depended on either a manually assembled `NutritionBrief` or the older chat action that reads the conversation state.

That left a gap: the Assistant could collect and show structured drafts, but did not have one clear proposal tool that consumes those draft objects directly.

## Decision

Add a reviewable proposal tool:

```text
create_nutrition_engine_dailyplan_proposal_from_drafts
```

The tool receives:

```text
profile_draft
preference_draft
proposal_preferences
current_nutrition_brief optional
raw_prompt optional
```

My Scoope composes these objects into the legacy `NutritionBrief` contract and then runs the existing internal nutrition-engine DailyPlan proposal flow.

## Rules

- The LLM may request this tool when the user asks to create a proposal and the relevant draft objects are available.
- The tool creates only reviewable `NutritionProposal` records.
- The tool never applies proposals.
- The tool never persists profile or preference memory.
- Persistent ficha/preference writes remain behind explicit approval tools.
- The nutrition engine remains the product source of truth for generated proposal content.

## Consequence

Proposal creation now follows the cycle architecture:

```text
LLM interprets user
↓
LLM fills draft objects through tools
↓
My Scoope syncs draft tool results into temporary chat state
↓
LLM requests proposal creation from drafts
↓
My Scoope composes NutritionBrief and creates a reviewable proposal
↓
UI can render the real proposal card
```

This keeps the Assistant in the role of product operator while preserving My Scoope's validation and review boundaries.
