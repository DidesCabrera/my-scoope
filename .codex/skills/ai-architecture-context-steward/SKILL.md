---
name: ai-architecture-context-steward
description: "Audit My Scoope's architectural coherence, canonical context, and onboarding path for a new AI. Use when Felipe asks whether the project is understandable, whether a code or product decision introduces architectural drift or hidden complexity, whether canonical documentation still matches implementation, or for a periodic AI cold-start/context audit. Do not use for ordinary code review or routine documentation updates that do not raise a project-comprehension concern."
---

# AI Architecture & Context Steward

Protect My Scoope's ability to be understood and changed safely by an AI arriving without prior conversation context. Optimize for **time to correct action**, not document volume: a new AI should quickly identify the current product, the authority for the affected domain, the relevant implementation, the decision history that still matters, and the validation boundary.

Communicate in Spanish unless the user requests another language.

## Respect authority and scope

1. Read the repository `AGENTS.md` first and obey its validation and Knowledge Center boundaries.
2. Begin with `docs/00_current/AI_README.md` and the compact packet for the actual
   mode, for example `scripts/manage.sh ai_project_context --compact --json
   --task-mode consult`. Add the domain filter when the scope is narrow. Use the
   complete context only for a genuinely cross-domain audit.
3. Establish claims from current implementation, tests, migrations, and executable contracts; then reconcile them with `docs/00_current/`, accepted decisions, and active cycles. Use Git history and Codex conversations to discover intent or change history, never as the sole proof of current behavior.
4. Treat `admin_knowledge/` and `docs/00_current/features/admin_knowledge/` only as human presentation. Never use them as architectural evidence or update them unless Felipe explicitly includes the Knowledge Center in the current request.
5. An audit request is read-only by default. Change product code, canonical documents, decisions, cycles, or external systems only when the user asks for those changes.
6. Request specialist review when correctness depends on deep domain knowledge that the available evidence cannot establish. Preserve the uncertainty instead of inventing architectural certainty.

## Choose the smallest useful mode

- **Change or decision review:** inspect a proposed design, diff, commit, or implementation path before integration and identify comprehension or coherence costs.
- **Canonical-context audit:** compare implementation and accepted decisions with current documentation and executable AI context.
- **Cold-start audit:** follow the documented entry path as if no prior project history were available and test whether it leads to a correct implementation and validation strategy.
- **Periodic project audit:** sample the most changed or highest-risk domains, then prioritize systemic drift rather than attempting to reread the entire repository without a reason.

For any mode, read [the comprehensibility rubric](references/comprehensibility-rubric.md). Apply only the sections relevant to the scope.

## Audit the evidence chain

1. State the audit question and the affected domain or decision boundary.
2. Build the smallest current-state baseline that can establish the claim. Start
   with the task packet and applicable current contract; add `PROJECT_STATE.md`,
   decisions, code, migrations, or tests only when they resolve a real boundary or
   uncertainty.
3. Identify the domain's authority, write path, consumers, permissions, terminology, failure boundaries, and owned validation. Record unknowns explicitly.
4. Compare the intended or observed change against that baseline. Look especially for competing sources of truth, duplicated domain rules, reversed dependencies, hidden cross-domain coupling, new one-off concepts, stale terminology, and validation that cannot prove the claimed boundary.
5. Classify every material finding as:
   - **Invariant violation:** contradicts a current architectural rule, authority, contract, or dependency boundary.
   - **Probable drift:** still works, but makes the correct path harder to discover or increases implicit knowledge and duplication.
   - **Intentional complexity:** may be justified, but its cost, authority, and rationale must be explicit and discoverable.
6. Recommend the smallest correction that restores a clear path. Prefer consolidating authority, vocabulary, navigation, and contracts over adding explanatory prose around avoidable complexity.
7. If updates are authorized, change the narrowest canonical sources and executable context needed. Do not rewrite history; mark superseded decisions or completed cycles using the repository's established conventions.
8. Validate at the layer that owns the risk. For documentation/context work, run
   focused document and context checks plus `scripts/manage.sh document_registry
   --strict`; follow the canonical testing policy before choosing any broader gate.

## Project-specific drift signals

Raise a finding when evidence suggests, for example:

- a second planning authority is introduced alongside the dated Calendar snapshot;
- the mobile client begins owning a domain rule that belongs to the backend;
- product behavior depends on the human Knowledge Center;
- a resource type bypasses the generic sharing, claim, or Inbox contract without an explicit decision;
- a current feature contract describes an intended flow that code and tests no longer implement;
- a completed baseline remains presented as an active source of requirements;
- two names describe one product concept, or one name hides materially different concepts;
- an AI must reconstruct a critical rule from scattered commits or conversations because no current source exposes it.

Do not flag complexity merely because it is unfamiliar or spans several files. Show the concrete wrong turn a new AI could take and the evidence that makes it plausible.

## Report for action

Lead with whether a new AI can act safely in the audited area. Include:

- scope, evidence inspected, and material coverage gaps;
- the current authority and shortest correct navigation path;
- findings ordered by risk, each with classification, evidence, likely AI failure mode, and smallest recommendation;
- intentional complexity that is adequately documented and therefore acceptable;
- canonical changes made, only when authorized;
- focused validation performed and what it does or does not prove.

Avoid a single opaque architecture score. Use the rubric's `clear`, `friction`, and `unsafe` assessments per dimension so the user can see exactly where comprehension degrades.

Success means a new AI can answer: what exists now, where truth lives, where to change it, which boundaries must remain intact, and how to verify the result—without relying on undocumented conversation history.
