# 0118 — AI Assistant Behavioral Alignment Cycle

Status: accepted
Date: 2026-07-14
Scope: AI Assistant identity, domain anchoring, initiative, tool governance and conversational UX

## Context

CM19-CM24 completed the LLM-native runtime alignment. The provider now uses native function calling, My Scoope owns validation and persistence, cards have explicit presentation boundaries, deterministic intake is isolated and real-provider checks protect operational invariants.

After that technical baseline passed, real conversation exposed behavior that was valid at the tool/state layer but weak as product UX:

- passive collection without progressing toward a result;
- repetitive confirmations and unnecessary recaps;
- broad general-purpose answers outside the My Scoope domain;
- exposure of internal tool names;
- unjustified tool use after ambiguous messages.

These problems should not be solved by restoring a deterministic questionnaire or adding a large set of brittle prohibitions.

## Decision

Create a dedicated cycle named:

```text
AI Assistant Behavioral Alignment & Tool Governance
```

The cycle uses prefix `BA` and separates behavioral product work from the completed CM runtime alignment.

The governing principle is:

```text
Direct the assistant with purpose, capabilities, state and boundaries;
do not direct it with a fixed conversational script.
```

The cycle covers:

- domain anchoring and assistant identity;
- capability abstraction instead of internal tool disclosure;
- restraint under ambiguous intent;
- goal-directed initiative;
- post-tool response quality and repetition control;
- invariant-based and real-provider behavioral validation.

## Boundaries

This decision does not authorize:

- backend semantic extraction to compensate for provider behavior;
- fixed question order or mandatory interview stages;
- hidden writes or weaker approval rules;
- disclosure of chain-of-thought;
- model fine-tuning as a prerequisite;
- treating off-domain social conversation as an error.

## Consequences

- CM19-CM24 becomes a completed technical baseline.
- Behavioral changes are reviewed as Agentic UX and tool-governance work.
- Prompts, tool descriptions, runtime metadata, fallbacks and tests may all participate, but no single layer should become a second conversational brain.
- Closure requires both invariant-based automated evidence and human transcript review.
