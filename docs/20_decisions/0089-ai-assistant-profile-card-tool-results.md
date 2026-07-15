# 0089 — AI Assistant profile card tool results in chat

Status: accepted
Date: 2026-07-09

## Context

CM03 introduced profile draft tools:

```text
read_user_profile_context
update_profile_draft
share_profile_draft_card
```

Those tools allow the LLM to fill a non-persistent profile draft, but the chat UI still needs a product-controlled way to show the resulting profile object. If the assistant only describes the updated draft in text, the experience falls back into the previous problem: the user cannot clearly see what My Scoope knows, what is pending and what would require approval.

## Decision

Controlled profile draft tool results may now carry a `profile_draft_card` payload. The chat surface renders that payload as a real message/card inside the conversation thread.

This keeps the separation clear:

```text
LLM interprets the user's message and requests tools.
My Scoope validates and executes the tool.
The tool result returns structured draft/card data.
The chat UI renders the card as a product object, not as LLM prose.
Persistent ficha updates still require explicit approval.
```

`update_profile_draft` now returns both:

```text
profile_draft
profile_draft_card
```

This prevents the assistant from needing a second tool call just to render the card after updating the draft. `share_profile_draft_card` remains available when the assistant needs to render an existing draft without changing it.

## Consequences

Profile cards are scrolleable chat artifacts, aligned with proposal cards.

The LLM should not manually describe the full ficha when a card exists. The UI is responsible for rendering the card from tool output.

The chat adapter exposes bounded tool results to the UI layer through internal metadata. This metadata is not provider-facing context; it is only used by My Scoope to render controlled tool outputs.

Duplicate profile cards are suppressed by comparing their visible field state, so a repeated tool result does not spam the chat thread.

This patch does not add persistent profile writes. CM05 remains responsible for the explicit approval/commit boundary.
