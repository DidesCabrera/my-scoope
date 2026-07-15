# 0102 · AI Assistant scripted replay scenarios

## Status

Accepted.

## Context

The AI Assistant client-memory/tool cycle exposed a runtime risk that ordinary unit tests do not catch early enough: a provider can return structured JSON, request tools, append cards and update `NutritionBrief`, while the chat UI still shows the wrong visible text or the conversation state silently diverges from the cards the user sees.

Manual browser testing caught those failures, but it made the user validate patches that should have been debugged before delivery.

## Decision

My Scoope will maintain scripted conversation replays with a fake provider as the default pre-UI validation path for AI Assistant behavior patches.

The replay layer must exercise the real runtime boundaries:

```text
fake provider response
→ provider JSON parser
→ tool execution
→ tool result metadata
→ NutritionBrief state sync
→ chat card rendering
→ final visible assistant text
```

It must not bypass the orchestrator, tool executors or chat engine with overly-perfect unit stubs.

## Implementation

CM18 introduces:

```text
notas/application/ai_intake/conversation_replay.py
notas/management/commands/debug_ai_assistant_conversation.py
notas/tests/test_ai_assistant_conversation_replay.py
```

Built-in scenarios currently include:

```text
dieta_con_ficha_tool_led
json_visible_boundary
```

The command can be used locally as:

```bash
python manage.py debug_ai_assistant_conversation --list-scenarios
python manage.py debug_ai_assistant_conversation --scenario dieta_con_ficha_tool_led --show-tools --show-state
```

The replay scenarios assert that:

```text
- raw provider JSON does not leak into user-visible text;
- tool results update the conversation-scoped NutritionBrief;
- profile/preference/proposal cards can be rendered from tool results;
- the final brief contains expected facts captured through tools;
- empty card-only assistant messages do not replace the last visible assistant text.
```

## Consequences

This does not replace real-provider testing. It gives My Scoope a deterministic way to catch system-level regressions before testing with OpenAI/Anthropic.

The recommended workflow for future Assistant patches is:

```text
1. run Django checks and directed unit tests;
2. run scripted replay scenarios;
3. inspect scenario output when a behavior fails;
4. only then validate manually with the real provider.
```

The fake provider validates My Scoope's runtime, not the provider's judgment. Real-provider testing remains necessary for tone, naturalness and spontaneous tool selection.
