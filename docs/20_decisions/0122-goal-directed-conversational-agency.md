# 0122 — Goal-Directed Conversational Agency

Status: accepted
Date: 2026-07-14
Scope: AI Assistant provider policy, intake progress context and reviewable proposal selection

## Context

The LLM-native runtime can preserve drafts, validate tools and block ambiguous operations, but it may still behave passively after the user has already stated a useful objective. A common failure is to acknowledge the current state, continue asking optional preference questions, or say that the work can advance without actually taking the available next step.

Examples such as:

```text
avancemos
con eso basta
sigamos con lo que ya tienes
```

should not become backend keywords or a deterministic routing table. They are semantic user decisions that the LLM must interpret in context.

## Decision

The provider receives a goal-directed agency contract:

1. derive an active objective from the latest clear user task;
2. carry it forward until it is completed, corrected or replaced;
3. prioritize the next useful My Scoope action over passive confirmation;
4. ask only for information that materially blocks the result;
5. treat a user decision to advance as permission to stop optional refinement;
6. when My Scoope reports that the work is ready and proposal creation is exposed, prefer creating the reviewable proposal in the same turn;
7. never claim proposal creation without a successful controlled tool result.

The intake provider context exposes product-computed progress through a bounded `work_progress` object. It reports proposal readiness and capability availability, but does not prescribe question wording, a tool sequence or the meaning of the latest user message.

## Boundaries

This decision does not:

- introduce a fixed question order;
- parse “advance” expressions with backend regexes or keyword matching;
- make optional preferences mandatory;
- bypass proposal validation or human review;
- auto-execute tools outside the provider-native tool loop;
- allow the assistant to claim a completed operation from plain text.

## Consequences

- The provider has enough state to distinguish blocking information from optional refinement.
- “Advance” can lead to an actual available action rather than another acknowledgement.
- Proposal readiness remains a domain calculation owned by My Scoope.
- Next-action selection remains LLM-led and observable through the existing tool governance contract.
- BA06 should replay ready and incomplete variants to verify real conversational behavior.
