# 0085 - AI Assistant Client Memory and Profile Objects

Status: accepted
Date: 2026-07-08
Amended by: `0086-ai-assistant-tool-oriented-operator.md`

## Context

LLM preview conversations showed that tone improvements alone do not solve the AI Assistant experience.

The assistant can sound warmer while still failing product expectations if it:

```text
- asks again for data already provided;
- says it understood a field but does not persist it in the internal state;
- treats profile data, proposal parameters and preferences as one flat form;
- hides what the system remembers from the user;
- writes permanent memory without explicit user approval.
```

The current AI intake should therefore evolve from slot capture toward object-based client memory.

## Decision

Adopt an object-based memory model for future AI Assistant intake work.

The durable rule is:

```text
Persistent profile != temporary proposal brief != visible chat transcript.
```

The AI Assistant may interpret natural language, including typos and conversational answers, but My Scoope must own state, validation and persistence.

The user-facing experience should expose relevant memory as cards/components, so the user can understand what the system knows, what is missing and what is only proposed as a draft.

## Memory objects

Future implementation should separate at least these concepts:

```text
Personal base profile
Body state
Food preference profile
Meal organization preferences
Proposal draft
Pending assistant memory
```

`number_of_meals` should not be treated as a mandatory permanent personal profile field. It is usually proposal-scoped or a soft meal-organization preference.

## Approval rule

Detected facts must be draft-first.

The assistant may prepare:

```text
profile_draft
preference_draft
proposal_preferences
```

Persistent updates require explicit user approval through application-controlled actions such as an “Actualizar ficha personal” button.

The LLM must not directly mutate persistent profile or preference models.

## UI/UX consequence

The chat should be allowed to render structured cards for information objects, for example:

```text
Ficha personal usada para esta propuesta
Preferencias alimentarias
Preferencias de organización
Datos pendientes para propuesta
```

This is not decorative UI. It is a product boundary that helps the user understand what My Scoope remembers.

## Technical consequence

Future patches should introduce explicit objects such as:

```text
work_intent
active_object
subject_source
profile_snapshot
profile_draft
preference_draft
proposal_preferences
field_sources
visible_ui_components
pending_approval_actions
```

This decision originally emphasized application-owned state boundaries. Decision `0086-ai-assistant-tool-oriented-operator.md` refines the implementation direction: the LLM should act as the user-facing assistant/operator through typed product tools, while My Scoope validates schemas, renders UI results and controls persistence.

## Non-goals

This decision does not immediately create a new persistent preference model.

It does not authorize silent profile updates from chat.

It does not move the chat UI out of `notas`.

It does not make the LLM the source of truth for nutrition calculation.

It does not reduce the LLM to a decorative text rewriter; the assistant may operate product capabilities through approved tools.

## Related documents

```text
docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md
docs/10_active_cycles/onboarding_nutrition_profile_cycle.md
docs/20_decisions/0020-ai-assistant-django-app-and-chat-engine.md
docs/20_decisions/0022-ai-assistant-structured-contracts.md
docs/20_decisions/0031-ai-assistant-safe-llm-context-builder.md
docs/20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md
```
