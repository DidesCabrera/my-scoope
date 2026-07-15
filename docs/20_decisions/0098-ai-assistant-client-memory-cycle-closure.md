# 0098 · AI Assistant client memory cycle closure

Status: accepted
Date: 2026-07-10
Area: AI Assistant, client memory, profile/preference drafts, tools, chat UX
Supersedes: none
Related decisions: 0085, 0086, 0088, 0089, 0090, 0091, 0092, 0093, 0094, 0095, 0096, 0097

## Context

The AI Assistant Client Memory & Profile Objects cycle started after repeated UX failures in the nutrition chat:

```text
- the assistant appeared to understand a fact but asked it again later;
- profile data, temporary chat facts and proposal preferences were mixed;
- cards could diverge from temporary state;
- prompt-only changes improved tone but did not fix product capability gaps;
- deterministic intake logic and LLM-visible text could behave like two competing brains.
```

The product direction changed from prompt tuning toward a tool-oriented assistant model.

## Decision

Close the CM00-CM13 cycle as completed and promote the durable contract to current docs:

```text
docs/00_current/features/ai_assistant/tool_oriented_client_memory.md
```

The accepted baseline is:

```text
The LLM is the assistant/operator.
My Scoope exposes real capabilities through tools.
Draft objects are visible and conversation-scoped by default.
Cards are product objects, not decorative assistant prose.
Persistent writes require explicit approval.
Tool results synchronize with temporary chat state.
Regression tests protect no-repeat behavior and approval boundaries.
```

## Implemented capability baseline

The cycle leaves these capability families in place:

```text
profile/client-memory tools:
- read_user_profile_context
- update_profile_draft
- share_profile_draft_card
- commit_profile_update (internal approval-only)

preference draft tools:
- update_preference_draft
- share_preference_draft_card

proposal preference/proposal tools:
- update_proposal_preferences
- share_proposal_preferences_card
- create_nutrition_engine_dailyplan_proposal_from_drafts

comparison/validation tools:
- compare_dailyplan_to_targets
- list_saved_comparisons
- read_saved_comparison
```

The assistant can now complete structured drafts, render cards from controlled tool results, create reviewable proposals from draft objects and read comparison artifacts. It does not silently persist profile or preference memory.

## Consequences

Future AI Assistant work should treat `tool_oriented_client_memory.md` as the current implementation contract.

The completed cycle document remains useful historical context, but it should not override current docs.

New work should prefer:

```text
- improving tool schemas and executors;
- adding visible object/card boundaries;
- adding regression tests for concrete UX failures;
- exposing existing product capabilities through safe tools;
```

over:

```text
- prompt-only personality fixes;
- regex-only intake patches;
- UI prose that claims a fact was captured when no tool/state captured it;
- direct LLM writes to persistent profile/preferences.
```

## Follow-up cycles

The next cycles should be smaller and more focused. Candidates:

```text
- persistent food/preference memory with approval UI;
- richer body-state and activity history models;
- final proposal apply/update tools;
- saved-comparison card rendering in chat;
- end-to-end conversation UX regression suite.
```

These are intentionally not included in the closed cycle.

## Validation baseline

The cycle is protected by the directed AI/tools test battery documented in:

```text
docs/00_current/features/ai_assistant/tool_oriented_client_memory.md
```

Broad changes should also run the full test suite when available.
