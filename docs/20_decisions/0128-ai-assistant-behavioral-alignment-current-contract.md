# 0128 — AI Assistant behavioral alignment current contract

Status: accepted
Date: 2026-07-15
Scope: BA07 current-contract promotion; BA00-BA06 and PT00-PT06 outcomes

## Context

The behavioral alignment work and the post-tool transport correction are now one operational baseline. BA02-BA06 established domain anchoring, product-language capability abstraction, restraint under ambiguous intent, goal-directed progression and response-quality invariants. PT00-PT06 then proved that repeated canned replies were largely caused by a broken provider continuation: opaque `call_id` values had been lowercased and no longer matched their outputs.

The corrected transport preserves provider identifiers, validates exact correlation, makes degradation observable and applies the same continuation checks in `FakeLLMClient`. The targeted live run `735444ac6d9b4ffe8087a5ec6e3f3e23` passed every automated check with `openai/gpt-5.4-mini-2026-03-17`. Its profile-aware fixture found weight and height available while age and sex were genuinely absent; the assistant did not re-ask known facts and the ambiguous-reference scenario executed zero tools. The working session accepted those transcripts for current-contract promotion.

## Decision

Promote the following as the current AI Assistant contract:

1. **Purpose over script.** Direct the LLM through My Scoope purpose, current state, available capabilities and boundaries. Do not rebuild a deterministic questionnaire in prompts or backend parsers.
2. **Product-language capabilities.** Internal tool names, schemas and MCP details are implementation contracts, not user-facing explanations.
3. **Operational restraint.** Tool availability is not authorization. Ambiguous references must be resolved from visible context or clarified before reads, writes or cards.
4. **Goal-directed progression.** Once a useful reviewable result is available, prefer advancing over repeated confirmation or indefinite collection of optional data.
5. **Visible-surface awareness.** Facts already present in profile context, drafts or cards must not be reintroduced as missing or visibly requested again.
6. **Tool-grounded claims.** Text alone never proves that My Scoope read, changed or created state; operational claims require the matching allowlisted tool result.
7. **Exact native continuation.** Provider `call_id` values are opaque and case-sensitive. Each native call has exactly one correlated output, and stateless reasoning replay preserves required encrypted content.
8. **Contract-faithful tests.** The fake provider rejects malformed continuation items before returning scripted copy, keeping offline tests aligned with production transport.
9. **Rare loud degradation.** Healthy tool turns are worded by the provider. `state_ack_only.v2` is a state-only emergency fallback, recorded as `degraded`; any occurrence blocks the live release gate instead of being counted as healthy.
10. **Profile-aware live fixtures.** Real-provider expectations derive from facts actually persisted for the selected staging user, while still failing if an available fact is lost between tool result and brief.

## Deferred work

- Improving nutrition recommendations, response personality or domain depth requires separate evidence and a newly scoped product cycle.
- Completing genuinely absent profile fields remains normal intake, not a behavioral regression.
- New linguistic variants should be added to scenario-owned invariants only when a real failure demonstrates the need; do not create a global regex semantic layer.
- Whole-project regression remains the final BA07 closure boundary. Promotion of this contract does not claim that the `full` suite has already run inside the focused export.

## Consequences

- `docs/00_current/` becomes the implementation source of truth for BA/PT outcomes.
- The BA plan remains in closure status until a patched `full` export passes the global regression suite.
- Future behavior patches should name the violated invariant and include fake-provider or live evidence appropriate to the risk.
- The focused `ai_behavior` mode remains the normal artifact for narrow behavioral work; `full` is mandatory at major architectural closure.
