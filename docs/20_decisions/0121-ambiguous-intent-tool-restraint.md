# 0121 — Ambiguous Intent and Observable Tool Selection

Status: accepted
Date: 2026-07-14
Scope: AI Assistant provider prompts, native function calls, execution guard and audit metadata

## Context

The LLM-native runtime can safely validate and execute allowlisted tools, but a technically valid function call may still be behaviorally unjustified. Short references such as:

```text
¿Qué pasó?
¿Y eso?
¿Por qué?
```

do not identify which My Scoope object should be read or which action should be performed. Treating them as implicit permission can produce unnecessary reads, draft updates, comparisons or cards.

The correction must not restore a deterministic backend questionnaire or attempt to interpret natural language with regexes.

## Decision

Provider-native function calls require a compact provider-only argument named:

```text
reason
```

The value is a brief statement of the clear operational intention that authorizes the call. It is observable evidence, not chain-of-thought.

The orchestrator:

1. removes `reason` before local tool validation and service dispatch;
2. blocks the call when the argument is absent or empty;
3. derives a stable operational reason code from the selected capability category;
4. records only the bounded code and summary in response metadata and the sanitized turn audit;
5. never records the function arguments as part of that audit evidence.

The provider policy also states that unresolved references require one brief clarification without tools. Reads and cards are treated as operations, not harmless defaults.

## Boundaries

This decision does not:

- expose tool names or selection reasons as normal user-facing copy;
- request or store private chain-of-thought;
- add backend semantic extraction, keywords or regex authorization;
- weaken allowlists, permissions, human review or service validation;
- pass the provider-only `reason` argument into product services;
- claim that a provider-written reason is sufficient behavioral evidence by itself.

Prompt policy and behavioral replays remain responsible for verifying that the assistant asks for clarification instead of inventing a plausible reason when intent is ambiguous.

## Consequences

- Native function schemas grow by one compact required string.
- Calls without observable intent evidence fail closed before dispatch.
- Tool selection can be inspected without prompts, raw provider payloads or tool arguments.
- Existing application services and typed tool arguments remain unchanged.
- BA06 should include replays where ambiguous references produce clarification and zero executed tools/cards.
