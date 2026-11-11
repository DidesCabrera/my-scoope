# Applied-AI capability lifecycle

Use this reference to take an AI idea from a user need to a governed capability.
The current authorities remain the AI Assistant feature contract, executable tool
registry, application services, MCP projection, and accepted architecture; this
reference does not replace them.

## 1. Outcome and evidence

Record the user request family, desired observable outcome, current workaround,
representative examples, failure evidence, affected product authority, consequence
of error, and how success will be verified. Distinguish a missing capability from
poor model behavior over an existing capability.

## 2. Mechanism selection

| Need | Preferred mechanism |
|---|---|
| Explain or converse from supplied context | Natural-language response with no false state claims |
| Present typed temporary state | Structured result or product-owned card |
| Read owner-scoped product state | Governed read capability |
| Generate nutritional composition | Reviewable `NutritionProposal` |
| Prepare deterministic product changes | Reviewable workspace patch or prepared action |
| Specialized, financial, destructive, or unsupported operation | Trusted-UI handoff |
| Long-running bounded work | Observable asynchronous job with idempotency and cancellation policy |
| Reuse by an authorized external AI client | MCP projection of an existing governed capability |

Prefer a product adapter over a growing collection of phrase-specific micro-tools.
Do not add a tool when the model does not need product state or an application
action. Do not use free text to imitate a state transition.

## 3. Capability contract

Define:

- stable capability name, purpose, request family, and expected outcome;
- input schema, null and missing semantics, allowed references, bounds, and version;
- owner, authentication, authorization, entitlement, and data-minimization rules;
- read, proposal, prepared mutation, commit, or handoff effect class;
- application service or query that owns the real behavior;
- result schema, visible product object, grounding evidence, and safe error states;
- idempotency, retry, timeout, cancellation, audit, usage, and cost behavior;
- assistant exposure, MCP exposure, or both, with any narrower MCP policy;
- evaluation scenarios, regression checks, observability, rollout, and rollback.

The provider does not receive unrestricted model methods, raw SQL, internal IDs it
does not need, or direct persistence authority. Every persistent effect must pass
through the application boundary and the accepted review or confirmation flow.

## 4. Implementation and projection

Implement the capability once at the application boundary. Register only the
provider-facing surface needed for the accepted outcome. When MCP exposure is
appropriate, project the governed capability and preserve authentication,
entitlement, ownership, schema, error, and audit semantics; do not reimplement the
domain operation in `mcp_server`.

Prompt and context changes should express stable behavioral policy or make an
existing capability discoverable. They must not replace validation, permissions,
calculation, or persistence logic.

## 5. Verification and release

Require contract tests, negative permission and argument tests, deterministic
assistant routing, outcome validation, failure and retry behavior, and MCP parity
when projected. Add or update a capability-catalog scenario and follow the staged
evaluation gate in `evaluation-and-release.md`.

Publish progressively. The capability is not complete because it appears in the
registry or because one conversation succeeded. Completion requires observed
outcome, preserved authority, regression evidence, and a monitored release state.
