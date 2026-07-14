# 0123 — AI Assistant response quality and repetition control

- Status: accepted
- Cycle: AI Assistant Behavioral Alignment
- Patch: BA05

## Decision

The provider remains responsible for natural wording, but My Scoope now gives it a compact response-quality contract:

- cards are already-visible response surfaces, not hidden data to repeat in prose;
- known facts are recapped only for review, correction, contradiction resolution or a decision that needs them;
- post-tool text explains the user-relevant consequence, not the raw payload or every submitted value;
- stock acknowledgements may be varied or omitted;
- a next action is mentioned only when it is concrete, available and relevant to the active objective.

The technical post-tool fallback follows the same boundary. It reports only bounded state consequences, does not echo user values, does not reproduce card contents and does not choose the next question.

## Rationale

Repeated confirmations such as “Perfecto. Dejé registrado...” made the assistant sound like a form and duplicated information that was already visible in chat cards. The solution must improve the behavioral contract without introducing exact response templates or another deterministic conversation planner.

## Consequences

- Provider prompts include BA05 quality principles and explicit card visibility semantics.
- Tool follow-up context instructs the provider to translate results into consequences.
- Local fallback acknowledgements use state-only wording and no longer enumerate captured values.
- Response wording remains adaptive; tests protect invariants rather than exact provider copy.
