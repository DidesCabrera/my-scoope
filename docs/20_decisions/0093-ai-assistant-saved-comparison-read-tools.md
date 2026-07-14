# 0093 - AI Assistant Saved Comparison Read Tools

Status: accepted
Date: 2026-07-09
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Related decisions: `0086-ai-assistant-tool-oriented-operator.md`, `0087-ai-assistant-validation-tool-executor.md`, `0092-ai-assistant-proposal-preference-tools.md`

## Context

The AI Assistant is moving from prompt-only behavior toward a tool-oriented product operator. CM02 already connected the validation executor for `compare_dailyplan_to_targets`, so the assistant can validate a DailyPlan against numeric targets.

However, My Scoope also has a product-level comparison capability based on `SavedComparison`. Users can save comparisons of foods, meals and daily plans, and those comparisons use snapshot payloads so they remain reviewable even if source entities later change.

For the assistant to help with comparisons in a grounded way, it needs read access to existing saved comparisons instead of speaking about comparisons abstractly.

## Decision

Expose saved comparisons to the AI Assistant through read-only tools:

```text
list_saved_comparisons
read_saved_comparison
```

These tools are owner-scoped, read-only and provider-exposed. They do not create, update, delete or re-run comparisons. They return stable comparison summaries and, when available, snapshot payloads.

`read_saved_comparison` also returns a renderable `saved_comparison_card` payload so future chat UI improvements can show comparisons as first-class objects in the conversation.

## Consequences

- The LLM can now help a user find and inspect saved comparisons.
- The assistant remains grounded in real My Scoope objects instead of inventing comparison summaries.
- Snapshot payloads remain the stable source for historical comparison review.
- No persistence or mutation is introduced by this patch.
- Future work can add comparison cards to the chat thread and additional comparator actions, such as creating a new saved comparison through explicit user intent.

## Boundaries

The tools must preserve these rules:

```text
writes_allowed = false
read_only = true
owner_scoped = true
```

They must not expose raw model mutation, raw SQL, or direct IDs outside the authenticated user's own `SavedComparison` records.
