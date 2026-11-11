# AI evaluation and release standard

Use this reference for assistant changes, model or prompt comparisons, tool and MCP
changes, fine-tuning proposals, and production rollout decisions. The current
baseline is `ai_assistant.evaluation_lab.v2`; extend it instead of creating a
parallel evaluation system without a demonstrated need.

## Evidence layers

Keep the layers distinct because they answer different questions:

1. **Contract tests:** schemas, permissions, ownership, effects, error handling,
   idempotency, transport, audit, and deterministic application behavior.
2. **Task dataset:** versioned user-request cases that verify outcome availability,
   routing, tool selection, arguments, and allowed effects without provider cost.
3. **Scenario preflight:** fixtures, canonical product projections, solver or data
   readiness, and expected ground truth before blaming a model.
4. **Live trajectories:** the production-like runtime and provider in an isolated
   staging account, repeated enough to observe nondeterminism.
5. **Automated quality checks:** grounding, completion, constraints, state changes,
   regression and safety invariants.
6. **Human quality review:** usefulness, naturalness, clarity, next step, cards, and
   domain quality not captured deterministically.
7. **Production signals:** outcome rate, feedback, failure and degradation rate,
   latency, cost, tool distribution, rollback triggers, and incident evidence.

A pass in one layer never substitutes for a missing later layer.

## Dataset governance

Version each case with purpose, request, setup, expected outcome, allowed effects,
forbidden effects, grading criteria, source, data classification, and owner. Keep
training or prompt-development examples separate from development evaluation and a
holdout set. Add observed failures as regressions after removing unnecessary
personal data, but do not disclose the hidden expected answer to the candidate.

Use synthetic or explicitly permitted de-identified data by default. Never place
secrets, raw provider payloads, health histories, or private conversations in the
repository. Retain hashes, structured outcomes, sanitized diagnostics, and links to
restricted evidence when needed.

## Candidate comparison

Freeze the dataset, runtime contract, tool surface, fixtures, and grader version
before comparing a model, prompt, context policy, or orchestration candidate. Record
candidate identity and configuration. Run the baseline and candidate with the same
repetition plan.

Evaluate per scenario:

- outcome completion and grounding;
- tool or mechanism choice and argument correctness;
- authorization, approval, and mutation invariants;
- conversational continuity and stop condition;
- response quality and product-language coherence;
- latency, tokens, estimated cost, retries, and degradation;
- consistency across repetitions.

Do not collapse hard gates into one average. A candidate fails when a priority
scenario violates authority, invents state, persists without approval, loses a
required outcome, or regresses below its accepted threshold. Compare cost and
latency among candidates that first pass quality and reliability.

## Environments

- **Local deterministic:** fake provider, contract tests, task dataset, fixtures,
  and no network or provider cost.
- **Isolated staging lab:** named test accounts, known fixtures, bounded provider
  budget, no production users, observable artifacts, and cleanup limited to objects
  created by the run.
- **Controlled production:** explicit cohort or flag, conservative limits, live
  monitoring, documented rollback, and no experimentation that bypasses product
  consent or accepted data use.

Fine-tuning or other model training is a separate candidate type. Require a lawful
and documented dataset, separation from evaluation data, reproducible build and
model identity, baseline comparison, cost estimate, safety review, and rollback to
the prior model. Prefer improving product contracts, tools, data, and context when
the failure does not require learned behavior.

## Advancement gate

A candidate may advance only when:

- the intended capability and affected authority are explicit;
- required deterministic and negative tests pass;
- every in-scope scenario passes all required repetitions;
- human review is complete where required;
- no unapproved persistent effect occurred;
- model, prompt, tool, schema, dataset, grader, and runtime versions are recorded;
- cost, latency, observability, rollout cohort, rollback trigger, and responsible
  reviewer are defined;
- unresolved failures have an owner and do not contradict the release claim.

Report `pending` when evidence or human review is missing. Report `blocked` only
when a concrete dependency prevents the next permitted step. Never label a model or
capability production-ready from a single successful transcript.
