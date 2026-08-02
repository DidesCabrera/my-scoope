# Decision 0163: AI runtime and tool schemas use explicit seams

Date: 2026-08-02
Status: accepted
Cycle: TDG05

## Context

The external LLM orchestrator combined turn coordination with configuration,
provider-response parsing and coercion. The canonical tool registry mixed registry
policy with more than a thousand lines of schemas. AI tool executors also imported
their neutral result type from `notas`, making the application boundary point in the
wrong direction.

## Decision

- Keep `ExternalLLMOrchestrator` and the canonical tool registry as stable facades.
- Move runtime configuration/limits and provider-response parsing/coercion into
  independent application modules.
- Own tool names separately from tool schema definitions.
- Group schemas by read operations, intake/drafts, reviewable proposals and prepared
  actions; merge them in the canonical registry where validation policy remains.
- Make `AIToolResult` an AI domain contract and retain the old `notas` import as a
  compatibility facade.
- Ratchet the remaining AI-to-`notas` production adapter imports so this
  transitional boundary cannot widen silently.

## Consequences

- The registry policy module falls from 1,312 to fewer than 300 lines.
- Provider parsing can be tested and changed without editing turn coordination.
- Capability schema changes have an explicit ownership module and keep the existing
  exported tool constants and registry APIs.
- Six AI executors no longer depend on `notas` merely to share a result data class.
- Product model, intake and prepared-action integration remains explicit transitional adapter
  work, not an unbounded circular dependency.
