# 0130 — Behavioral replays and real-provider UX gate

## Status

Accepted in BA06.

## Decision

Behavioral alignment is protected by two complementary evidence layers:

1. deterministic fake-provider replays that enforce product invariants without asserting exact prose;
2. targeted real-provider transcripts that combine hard automated checks with explicit human UX review.

A real-provider report that passes automated checks remains `awaiting_manual_review`. It is not evidence of UX approval until a reviewer reads the transcript and records a disposition outside secrets and provider credentials.

## Protected outcomes

The BA06 catalog covers:

- brief, polite off-domain redirection without tools or cards;
- capability explanations in product language, without internal function names;
- clarification of ambiguous references before any product operation;
- grouped-fact and card pacing;
- change of direction and progress without optional-preference loops;
- tool-error recovery without technical leakage;
- repeated mechanical openings within an explicit limit.

## Boundaries

- Replays assert invariants and fragments only where needed; they do not freeze exact wording.
- Live validation consumes provider usage and must require `--live` plus one explicit staging user.
- API keys and provider credentials never belong in reports or patches.
- Automated success does not replace human review of tone, usefulness and pacing.
