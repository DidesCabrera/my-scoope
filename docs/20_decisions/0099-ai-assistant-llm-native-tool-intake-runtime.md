# 0099 · AI Assistant LLM-native tool intake runtime

Status: accepted
Date: 2026-07-10
Area: AI Assistant, tool runtime, nutrition intake, chat UX
Related decisions: 0086, 0096, 0098

## Context

After the client-memory cycle closed, real chat testing still exposed a runtime mismatch:

```text
- the assistant could greet naturally but then jump into nutrition intake too early;
- the LLM could appear to understand a goal while the next turn asked for it again;
- the provider context still carried deterministic `conversational_intake` suggested questions;
- using the user's ficha was not represented as a tool result that updated the conversation state;
- profile cards and brief state could still diverge when profile context was read-only only.
```

The product direction is that the LLM is the assistant/operator. The system should provide tools and typed objects, not a parallel deterministic intake script.

## Decision

In LLM modes, remove deterministic suggested intake questions from provider-facing context.

The LLM receives:

```text
- current draft objects;
- tool-oriented operating rules;
- tool schemas with field descriptions;
- recent conversation messages.
```

It should decide the next natural question and must use tools to record user facts.

The runtime must not send `conversational_intake.suggested_visible_questions` to the provider in LLM-led intake. That metadata is allowed to remain for deterministic mode or internal code, but it is no longer a provider instruction.

## Tool boundary

When the user says they want to use their ficha/profile/personal data, the assistant should call:

```text
read_user_profile_context
```

That tool now returns:

```text
profile_context
profile_draft
profile_draft_card
nutrition_brief_patch
```

So reading the ficha is not just informational; it also creates a conversation-scoped draft/card and marks:

```text
subject_source = self_profile
ppk_weight_source = profile_current_weight
```

This keeps future turns from asking again whether to use the ficha.

## Consequences

The backend still validates tool arguments and may tolerate minor argument noise for safety, but the runtime no longer relies on deterministic semantic parsing to decide the next LLM question.

The durable rule is:

```text
LLM interprets and asks.
Tools record.
NutritionBrief syncs tool results.
Cards render product objects.
Deterministic intake does not script the LLM runtime.
```

## Validation

The patch adds/updates tests that verify:

```text
- provider context no longer includes conversational_intake;
- tool_oriented_intake declares deterministic questions removed;
- read_user_profile_context returns profile draft/card and source patch;
- read_user_profile_context tool results sync profile fields and subject_source into NutritionBrief;
- existing AI/tools directed battery stays green.
```
