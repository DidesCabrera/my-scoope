# CML00-CML08 Consumer Mobile Launch Cycle

Status: active
Date: 2026-08-05
Cycle code: CML

## Objective

Launch My Scoope as a consumer-first React Native iOS product for disciplined gym
users who weigh food and follow a nutrition program. Product foundations land
before mobile interfaces; the dated program becomes executable before progress
or adjustment claims; App Store work remains separate from general product work.

## Invariants

- The consumer following their own program is the primary mobile customer.
- Nutritionist, invited-member and seat-purchase flows are outside the MVP.
- `Program` is a template; `ProgramCalendarization` is the lived program.
- Past calendarized snapshots and execution evidence are never silently changed.
- Adjustments are reviewable and affect only eligible future days.
- React Native reuses the product's visual grammar, not Django HTML/CSS.
- Django application services remain the business-rule authority.
- OCR and AI outputs require review before persistent writes.
- `accounts.AccountSubscription` remains the entitlement authority.
- Every model has an explicit account-deletion retention policy.

## Patch sequence

| Patch | Status | Product/App Store | Exit evidence |
| --- | --- | --- | --- |
| CML00 · Consumer baseline | completed | Product | Accepted B2C brief, MVP boundary, success measures and durable decisions. |
| CML01 · Safety and privacy | completed (repository) | Product + review prerequisite | Shared runtime secret, reproducible frontend bundle, account deletion with exhaustive retention classification, legacy credit monitoring evidence and current project state. |
| CML02 · Vertical mobile API | completed (repository) | Product/mobile | Versioned OpenAPI contract for auth, profile, active program, Today, weight, foods, durable AI submit/poll, entitlements and deletion. Mobile OAuth is audited from the existing PKCE baseline and gains rotating device sessions. Adherence waits for the CML04 execution model. |
| CML03 · React Native and visual system | planned | Mobile | Expo development build, extracted visual tokens/card grammar and the on-device login → onboarding → Today → check-in → weight path against staging. |
| CML04 · Lived program | planned | Product/mobile | Calendarization owns dated plans, meal execution, reminder coordination, measurement context, reviews and prospective audited adjustment revisions. |
| CML05 · Nutrition-label capture | planned | Product/native | On-device OCR normalizes label values, exposes uncertainty and creates a private food only after user confirmation. |
| CML06 · B2C subscriptions | planned | Product/App Store | Independent Apple/Mercado Pago evidence aggregates deterministically into `AccountSubscription`; StoreKit purchase, restore and lifecycle reconciliation pass sandbox. |
| CML07 · iOS capabilities | planned | App Store | Signing, Apple login where applicable, camera permissions, local notifications/APNs, Keychain, privacy manifests and sanitized crash reporting pass device QA. |
| CML08 · Review readiness | planned | App Store | Privacy labels, consent, metadata, screenshots, demo program, internal/external TestFlight and complete reviewer notes. |

## Calendarization target

```text
Program template
  -> ProgramCalendarization
      -> immutable CalendarizedDay plan snapshot
      -> planned meals and times
      -> logical reminder events
      -> meal/day execution evidence
      -> measurements in program context
      -> periodic review
      -> confirmed revision of future unexecuted days
```

The current durable event/delivery split remains. Mobile local notifications and
APNs become delivery channels coordinated from the same calendarization schedule;
permission denial degrades gracefully.

## CML00-CML01 closure evidence

- `docs/00_current/CONSUMER_PRODUCT_BRIEF.md` fixes the consumer, outcome,
  exclusions, visual direction and launch measures.
- Decisions 0173-0175 make the consumer-first client, React Native visual
  translation and lived-program ownership durable.
- All Render Django processes inherit one generated `SECRET_KEY` from the same
  environment group; a regression contract protects that topology.
- Frontend CI rebuilds the committed async-job bundle and rejects drift.
- Profile exposes authenticated account deletion with deliberate confirmation,
  immediate access revocation and an identity-free receipt.
- `account-deletion.v1` classifies every installed concrete model; CI fails when
  a new model lacks an explicit erase, anonymize or retention decision.
- Legacy AI credit models remain read-only outside reconciliation and deletion;
  the authority scan explicitly excludes `.venv` and the reconciliation command
  remains the observation surface before physical table removal.
- The fast structural gate, frontend tests/build, all 59 account tests and the
  complete 1,686-test Django suite pass locally on 2026-08-05.

Repository completion does not claim external operational approval. Before a
production/App Store release, My Scoope must still prove a real backup restore,
apply the Render Blueprint safely in staging and obtain accounting/legal approval
for country-specific financial retention periods. Apple subscription management
and Sign in with Apple token revocation belong to CML06-CML07.

## CML02 closure evidence

- `/api/v1/` is owned by the new `mobile_api` interface app and uses the stable
  `{ok, data, error}` envelope.
- Django Ninja generates `docs/00_current/api/mobile-v1.openapi.json`; the fast
  CI gate rejects contract drift.
- Existing PKCE S256 remains mandatory. Mobile clients gain device-bound access
  tokens, rotating refresh-token families, reuse detection and per-device
  revocation without changing the ChatGPT/MCP flow.
- The consumer vertical includes session, onboarding, profile, entitlements,
  active program, Today, weights, food search, AI async submit/poll and account
  deletion.
- API code calls existing account, calendarization, food-picker, body-metric, AI
  queue and deletion services. No parallel domain calculations were introduced.
- Adherence remains absent by design until CML04 owns execution evidence inside
  the calendarized program.

CML03 is the next implementation patch. Staging must still register the mobile
OAuth public client and its HTTPS universal-link callback before a device can
complete the authorization flow.

## Release order

```text
Web release 1: CML00-CML01
Web release 2: CML02
Web release 3: CML04 backend
Internal mobile 1: CML03
Internal mobile 2: CML04
Internal mobile 3: CML05
Internal TestFlight: CML06-CML07
External TestFlight and submission: CML08
```

## Deferred by design

- Nutritionist workspaces, invited clients and seats.
- Android.
- Barcode lookup.
- HealthKit writes, widgets, Apple Watch, biometrics and Live Activities.
- Generic offline mutation replay.
- Physical removal of legacy tables before the CML01 observation and recovery
  evidence exists.
