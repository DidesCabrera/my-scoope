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
| CML03 · React Native and visual system | completed (repository; device gate pending) | Mobile | Expo development build, extracted visual tokens/card grammar and the login → onboarding → Today → check-in preview → persisted weight path. Physical staging proof remains external. |
| CML04 · Lived program | completed (repository) | Product/mobile | Calendarization owns dated plans, append-only meal execution, reminder coordination, measurement context, frozen reviews and prospective audited adjustment revisions. Native notification delivery remains CML07. |
| CML05 · Nutrition-label capture | completed (repository; device gate pending) | Product/native | Apple Vision OCR stays on-device, normalizes label values, exposes uncertainty and creates an idempotent private food only after user confirmation. |
| CML06 · B2C subscriptions | planned | Product/App Store | Independent Apple/Mercado Pago evidence aggregates deterministically into `AccountSubscription`; StoreKit purchase, restore and lifecycle reconciliation pass sandbox. |
| CML07 · iOS capabilities | planned | App Store | Signing, Apple login where applicable, camera permission and on-device OCR verification, local notifications/APNs, Keychain, privacy manifests and sanitized crash reporting pass device QA. |
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

## CML03 closure evidence

- `mobile/` is a strict-TypeScript Expo SDK 57 client configured for development
  builds, Expo Router and future bounded native modules.
- `myscoope.visual-grammar.v1` translates dark surfaces, cards, spacing, radii,
  entity colors and nutrition colors into a platform-neutral JSON contract used
  directly by native primitives.
- OAuth authorization code + PKCE runs through the system browser. Access and
  rotating refresh tokens are device-bound, stored with SecureStore and managed
  behind one independently tested session manager.
- The native path includes login/signup handoff, nutrition onboarding, Today,
  active calendarization, daily plan/macros, planned meal cards, check-in preview,
  real weight writes and recent weight history.
- The original check-in preview was intentionally non-persistent; CML04 later
  replaced it with immutable evidence owned by the lived calendarization.
- Mobile CI installs from its lockfile and runs lint, strict TypeScript, contract
  tests, session rotation tests and a Metro bundle export.

Repository completion does not claim on-device staging evidence. The current
machine lacks a full Xcode installation, and staging must register the mobile
OAuth public client plus its exact callback. Once those external prerequisites
exist, `npm run ios` is the bounded device smoke for CML03. CML04 builds on that
repository baseline without claiming this external device gate.

## CML04 closure evidence

- `ProgramCalendarization` now owns append-only meal execution events. A
  correction appends a reset instead of rewriting history, and idempotency keys
  make retries safe.
- Today derives the current state of each planned meal plus a rolling seven-day
  adherence summary from that immutable evidence.
- Weight writes continue through the established user-owned `WeightLog` service;
  a separate context record relates each measurement to the lived program and
  dated day without duplicating the measurement authority.
- Periodic reviews freeze adherence, measurements and the user's energy, hunger
  and training-performance scores at submission time.
- Prepared adjustments are explicit revisions with before/after snapshots. The
  consumer API can approve or reject them, but cannot author arbitrary plan
  changes. Approval revalidates that every affected day is strictly future and
  has no execution evidence, then recalculates its reminder events.
- Reminder preferences and upcoming logical events are visible and editable from
  the mobile client. The calendarization remains the schedule authority; local
  notifications/APNs attach as delivery channels in CML07.
- The API/OpenAPI contract, deletion-policy manifest, migration, domain-boundary
  rules and focused backend/mobile tests protect the new behavior.
- Local closure on 2026-08-05 passed the 95-test fast gate, all 1,711 Django
  tests, mobile lint, strict TypeScript, five Node contract/session tests and the
  12-route Expo web export.

Repository completion does not claim native alarm delivery or physical-device
evidence. Those require the CML07 notification permission/channel work plus the
existing staging OAuth and Xcode prerequisites. CML05 builds on this baseline.

## CML05 closure evidence

- `expo-camera` captures a temporary image only after an explicit permission
  action; refusing permission degrades to manual review.
- An auto-linked, iOS-only Expo module uses Apple Vision locally and returns text,
  bounding boxes and confidence without a network OCR provider.
- The TypeScript normalizer handles decimal commas, per-100-gram values,
  per-serving conversion and common two-column labels. Missing, uncertain and
  energy-inconsistent values remain visible for correction.
- The review form is the only path to persistence. It sends confirmed normalized
  facts, not the photo or raw OCR text.
- The API reuses the food entitlement and creates only private, unverified,
  solver-disabled foods. `FoodLabelCaptureReceipt` provides idempotency and
  provenance without retaining the image or recognized text.
- Backend ownership, account deletion, OpenAPI, native configuration, 9 mobile
  tests, the 13-route Expo export, 95 fast-gate tests and the complete 1,717-test
  Django suite protect the repository contract.

Repository completion does not claim an iOS binary/device pass. The local machine
does not have the iPhone simulator SDK, so Vision compilation, camera behavior and
final permission/privacy review remain explicit CML07 gates. CML06 is the next
implementation patch.

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
