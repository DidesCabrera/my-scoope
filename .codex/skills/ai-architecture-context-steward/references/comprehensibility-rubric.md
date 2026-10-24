# Comprehensibility rubric

Use this rubric to evaluate the dimensions relevant to the requested scope. Do not convert it into a mechanical checklist or average the results into one score.

Assess each relevant dimension as:

- **clear:** the documented path leads efficiently to evidence that supports the correct action;
- **friction:** the correct action is discoverable, but requires avoidable inference, duplicate reading, or undocumented context;
- **unsafe:** a reasonable new AI could follow the available guidance and make a materially incorrect change or claim.

## 1. Authority clarity

- Is there one identifiable source of truth for state and behavior?
- Are templates, projections, caches, provider evidence, and human explanations distinguished from authority?
- Do write paths and conflict-resolution rules reinforce the stated authority?

Strong evidence: models and constraints, service/write paths, migrations, contract tests, accepted architectural decisions.

## 2. Concept and vocabulary coherence

- Does one product concept have one stable name across current docs, APIs, code, and UI?
- Are similarly named concepts explicitly distinguished?
- Can historical vocabulary be mistaken for the current model?

Record the wrong implementation choice that ambiguous terminology could cause.

## 3. Boundary and dependency integrity

- Do domain rules live in their intended layer?
- Are clients consuming contracts rather than recreating policy?
- Does a new special case bypass an existing generic contract?
- Are human presentation, operational evidence, and product behavior kept separate?

Inspect imports and call paths when a written boundary is not enough to prove compliance.

## 4. Navigation and locality

- Does `AI_README.md` route the task to the right current documents?
- Can an AI find the implementation, ownership, permissions, and tests without searching the repository blindly?
- Are critical rules colocated with their contract or linked from the canonical entry point?

More files are not automatically worse. Penalize only unnecessary search, duplication, or misleading routes.

## 5. Temporal and decision clarity

- Can an AI distinguish current behavior, active work, planned work, completed delivery history, and superseded decisions?
- Do accepted decisions explain intentional non-obvious complexity?
- Have durable outcomes been promoted from cycles into current contracts?

Git commits and Codex conversations may reveal why a change happened. Verify the surviving result in current sources before presenting it as truth.

## 6. Validation discoverability

- Can an AI determine the smallest check that owns the changed risk?
- Does the available test prove the claimed contract rather than a nearby implementation detail?
- Are code, deployment, provider, and device evidence correctly separated?

A validation command that is difficult to discover is itself comprehension friction.

## 7. Executable context fidelity

- Does `ai_project_context` expose the current state, live cycles, recent decisions, transitions, and relevant domain context without leaking private data?
- Does `project_status` distinguish local capability evidence from live environment evidence?
- Would their output steer an AI toward the same architecture described by the code and current documents?

Use `document_registry --strict` to detect registry inconsistencies, but do not treat registry validity as proof that document content is correct.

## 8. Cold-start path

For a cold-start audit, begin from the canonical entry point rather than from remembered conversations. Test whether the evidence lets an AI:

1. summarize the affected capability and its current authority;
2. locate the main read and write paths;
3. identify permissions, invariants, and failure boundaries;
4. distinguish current behavior from history and future intent;
5. choose the correct focused validation;
6. name the remaining uncertainty without guessing.

Capture concrete friction: misleading links, competing descriptions, missing entry points, terminology shifts, or facts available only in history. If an independent AI evaluation is desired, use a subagent only when the user or current repository instructions authorize delegation.

## Finding format

For each material finding, record:

```text
Assessment: clear | friction | unsafe
Classification: invariant violation | probable drift | intentional complexity
Evidence: current files, contracts, tests, or runtime evidence
Likely AI failure: the plausible wrong conclusion or change
Recommendation: the smallest action that restores a clear path
Confidence: high | medium | low, with the missing evidence when relevant
```

Do not report wording preferences as architectural findings unless they create a plausible wrong action.
