# Nutrition-label AI reliability cycle

Status: completed in repository; staging and TestFlight validation pending
Date: 2026-09-03

## Objective

Deliver reliable nutrition-label digitization with a predictable credit price,
hidden stronger-model escalation, explicit image consent, gallery support and
measurable operational quality.

## Ordered execution

1. **Baseline and contract** — audit the existing Apple Vision flow, food command,
   credit wallet, provider adapter, privacy copy and Expo 57 APIs.
2. **Server extraction** — add strict multimodal structured output, deterministic
   normalization, quality gates and Luna-to-Sol escalation.
3. **Economic safety** — reserve one fixed price, consume only on useful output,
   release on total failure and make retries idempotent.
4. **Mobile acquisition** — support camera and gallery, re-encode/resize locally,
   use Apple Vision only as a comparison signal and keep manual entry.
5. **Retention choice** — default to no storage; verify, retain, view and delete
   only the processed image after explicit opt-in.
6. **Observability** — persist scan-level outcomes and per-provider-call usage;
   expose the 30-day escalation/resolution/cost report.
7. **Privacy and contracts** — update consent, privacy policy, App Store metadata,
   generated OpenAPI, migration and accepted decision.
8. **Verification and rollout** — pass focused/full automated suites, merge into
   staging, deploy, then smoke-test camera and gallery on a physical iPhone through
   TestFlight before broader rollout.

## Acceptance gates

- One successful scan produces exactly one fixed charge, regardless of one or two
  model calls.
- Total extraction failure produces zero net charge.
- Replaying a completed idempotency key produces no new provider call or charge.
- The user can edit all values before creating a food.
- No image is retained by default; an opted-in copy is owner-only and deletable.
- Metrics distinguish primary success, escalated success and unresolved failure.
- Real-label launch target: at least 90% usable results, with escalation reviewed
  weekly and investigated above 20%.

## Physical validation set

Use at least 30 labels: Spanish and English; per-100-g and per-serving; dual-column;
decimal comma/point; glossy packaging; curved packages; small typography; kcal/kJ;
sodium in mg/g; low light; and deliberate non-label/blurred controls. Record whether
the candidate was usable before edits, which fields needed edits and whether the
scan escalated (from the internal report, not the app UI).
