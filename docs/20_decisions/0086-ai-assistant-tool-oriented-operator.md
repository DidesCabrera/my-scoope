# 0086 - AI Assistant as Tool-Oriented Product Operator

Status: accepted
Date: 2026-07-09
Related cycle: `docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md`
Amends: `0085-ai-assistant-client-memory-profile-objects.md`

## Context

Early AI intake patches improved tone and visible profile cards, but the assistant still failed in important ways:

```text
- it could say a field was understood while the system asked it again later;
- deterministic intake logic and LLM-generated text could disagree;
- profile, preference and proposal data were still being treated as slots instead of product objects;
- capabilities that already exist in My Scoope, such as comparisons, were not available to the assistant as tools.
```

A purely deterministic controller would reduce the LLM to a text formatter. That does not match the product vision.

The AI Assistant should be an assistant in the product sense: it should help the user perform actions that My Scoope can actually perform.

## Decision

Adopt a tool-oriented AI Assistant model.

The durable rule is:

```text
The LLM assists and operates through tools.
My Scoope exposes safe tools, validates contracts, renders UI objects and controls persistence.
```

The LLM should be allowed to understand the user, complete drafts and request product actions. The system should not run a competing interviewer that asks different questions from the assistant.

## Architectural principle

Do not design the assistant as:

```text
user -> rigid extractor -> deterministic controller -> LLM text rewrite
```

Design it as:

```text
user -> LLM assistant -> typed product tools -> validated state/UI/action
```

The LLM can be the semantic interpreter and conversational operator. Tools are the product boundary.

## Tool contract categories

Future implementation should expose capabilities through explicit tool families.

### Profile and client memory tools

```text
read_user_profile_context
update_profile_draft
share_profile_card
propose_profile_update
commit_profile_update_after_approval
```

These tools let the assistant read profile context, complete profile drafts from natural language and request explicit approval before persistent writes.

### Preference tools

```text
read_user_preference_context
update_food_preference_draft
update_meal_organization_draft
share_preference_card
commit_preference_update_after_approval
```

These tools let the assistant learn dietary patterns, avoided foods, preferred foods and organization preferences as visible memory.

### Proposal tools

```text
update_proposal_preferences
create_nutrition_proposal
share_proposal_card
```

These tools let the assistant move from conversation to real proposal generation using explicit profile/preference snapshots.

### Comparator tools

```text
list_comparable_plans_or_proposals
compare_plan_to_plan
compare_proposal_to_targets
share_comparison_card
```

These tools let the assistant use existing comparison capabilities instead of speaking about comparisons abstractly.

### Read-only context tools

```text
list_user_proposals
read_dailyplan
read_proposal
list_food_catalog
```

These tools let the assistant ground its help in actual user/system data.

## Tool design requirements

Each tool should declare:

```text
name
purpose
input schema
output schema
read/write level
approval requirement
allowed side effects
UI component result, if any
error modes
observability event
```

Writes should be draft-first unless the action is explicitly approved, reviewable and reversible.

## Persistence rule

The LLM must not directly mutate persistent user profile or preference data.

The LLM may request:

```text
update_profile_draft
update_preference_draft
propose_profile_update
propose_preference_update
```

A persistent write requires application-controlled approval, for example a button rendered in the chat card.

## UI consequence

Tool results may render UI cards inside the chat thread.

Examples:

```text
Ficha personal para esta propuesta
Preferencias alimentarias
Preferencias de organización
Comparación de planes
Propuesta nutricional
```

Cards are not decorative. They are the visible representation of product objects the assistant is using or preparing.

## AI behavior consequence

The assistant should not say it completed or remembered something unless the relevant tool result confirms it.

The assistant should not ask again for data that exists in:

```text
profile context
profile draft
preference draft
proposal preferences
tool results from the same conversation
```

If the assistant needs a capability, the correct product response is to add or improve a tool, not to add more prompt text only.

## Non-goals

This decision does not authorize unbounded agent behavior.

It does not allow silent persistent writes.

It does not require all tools to be implemented immediately.

It does not remove the existing `notas` chat surface.

It does not make the LLM the source of truth for nutrition calculations; calculators and solvers remain product services.

## Consequences for the active cycle

The active Client Memory cycle should be treated as a tool-oriented cycle.

The next implementation work should prioritize:

```text
1. inventory existing product capabilities that the assistant should expose;
2. define schemas for profile/preference/proposal/comparison tools;
3. implement profile draft tools before further prompt tuning;
4. render tool-result cards inside the chat thread;
5. add tests around tool-led memory and approval boundaries.
```

## Related documents

```text
docs/10_active_cycles/ai_assistant_client_memory_profile_objects_cycle.md
docs/20_decisions/0085-ai-assistant-client-memory-profile-objects.md
docs/20_decisions/0023-ai-assistant-tool-registry.md
docs/20_decisions/0024-ai-assistant-llm-orchestrator-v1.md
docs/20_decisions/0032-ai-assistant-read-only-tool-executor.md
docs/20_decisions/0033-ai-assistant-llm-read-only-tool-loop.md
docs/20_decisions/0034-ai-assistant-reviewable-proposal-tool-executor.md
```
