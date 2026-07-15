# 0088 — AI Assistant profile draft tools

Status: accepted
Date: 2026-07-09

## Context

The AI Assistant client-memory cycle moved the product away from prompt-only fixes and toward a tool-oriented assistant model.

The assistant must be able to understand profile facts from natural language and complete a structured draft, but it must not silently mutate the user's persistent ficha personal. The previous chat/intake behavior showed that visible text, internal brief state and profile cards can drift apart when there is no explicit tool contract for profile context and profile draft updates.

## Decision

Add profile-related tools to the AI Assistant tool system:

```text
read_user_profile_context
update_profile_draft
share_profile_draft_card
```

These tools establish a controlled boundary:

```text
LLM understands and fills a draft through tools.
My Scoope validates arguments, returns structured draft/card payloads and keeps persistence disabled.
Persistent ficha updates require a later explicit approval/commit tool.
```

The tool categories are extended with a new non-persistent category:

```text
draft
```

Draft tools are not read-only, because they transform structured draft state, but they are also not persistent writes. They must expose metadata such as:

```text
writes_allowed = false
persistent_profile_updated = false
draft_only = true
requires_user_approval_for_persistence = true
```

## Consequences

The assistant can now use a product capability to complete profile drafts instead of relying on a parallel deterministic interviewer or fragile regex-only parsing.

The profile draft object is explicitly separate from:

```text
- the persistent Profile / WeightLog records;
- proposal preferences such as number of meals;
- future food preference memory.
```

`read_user_profile_context` is a read tool and can safely expose persisted profile context to the LLM.

`update_profile_draft` and `share_profile_draft_card` are draft tools. They may prepare structured data and renderable card payloads, but they cannot update the permanent ficha.

A later patch must add the approval/commit boundary before any permanent profile mutation is performed through assistant tools.
