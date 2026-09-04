# Nutrition-label capture

Status: current
Date: 2026-09-03

## Product contract

The consumer app turns a camera or gallery image of a printed nutrition table
into a reviewable private food. AI processing is a convenience over the manual
food form, not an authority and not a photo-of-a-meal calorie estimator.

```text
camera or gallery selection
  -> resize + JPEG re-encode on device (metadata removed)
  -> optional Apple Vision candidate on iOS
  -> OpenAI primary extraction (Luna)
  -> deterministic normalization and validation
  -> hidden Sol escalation when quality checks fail
  -> editable user review
  -> private, unverified, solver-disabled Food
```

The user sees one configured price, currently two credits per successful scan.
Switching to the stronger model is an internal My Scoope cost and never changes
that price. A scan that neither model can resolve releases its reservation and
charges zero credits. Manual entry remains available without an AI charge.

## Image and consent boundary

Before starting a scan, the app explains that a reduced, re-encoded copy will be
sent temporarily to OpenAI. The request carries explicit consent. The server
accepts JPEG, PNG or WebP, rejects images outside the size/dimension contract and
sends the provider a stateless `store: false` request.

The original image is never persisted by My Scoope. The provider response and
raw OCR text are not stored. Only the normalized candidate, image SHA-256 digest,
models used, resolution status, credits and cost metadata remain in the analysis
audit record.

After a successful analysis, the user may opt in to retain the processed image.
The server verifies that its digest matches the completed analysis and stores at
most 1.5 MB in the private capture receipt. The owner can view and delete it from
the food detail. Account deletion erases the analysis and cascades through the
food receipt. Database storage is acceptable for the bounded first release; move
to private object storage before retained-image volume becomes material.

## Extraction, validation and escalation

The model must return a strict JSON schema and may report `ambiguous`,
`not_nutrition_label` or `image_unreadable`; it is instructed never to guess.
Server code then:

- requires protein, carbohydrates, fat and a supported basis;
- converts per-serving values only with a positive printed serving weight;
- converts kJ to kcal and sodium grams to milligrams;
- rejects impossible macro, energy and sodium ranges;
- compares declared energy with macro-derived energy;
- compares the primary result with the optional on-device candidate;
- escalates when the primary result is invalid, low-confidence, internally
  inconsistent or materially disagrees on multiple core macros.

If Sol fails but the primary candidate remains valid, the primary candidate is
shown with an additional review warning. If no valid candidate exists, the scan
fails without a charge and the same manual form remains available.

## API and persistence

- `GET /api/v1/foods/label-captures/config` returns fixed price, current balance
  and availability.
- `POST /api/v1/foods/label-captures/analyze` accepts the processed image,
  consent, dimensions, idempotency key and optional local candidate.
- `POST /api/v1/foods/label-captures` persists only user-confirmed normalized
  values and, when explicitly selected, the verified processed image.
- `GET|DELETE /api/v1/foods/label-captures/{receipt_id}/image` is owner-scoped.

Both AI analysis and food creation are idempotent. The image API requires the
same authenticated owner, and mutating paths require `mobile:write`.

## Metrics and operating loop

`FoodLabelAIAnalysis` is the scan-level source of truth. `AIUsageEvent` records
each provider call with its actual model, usage, latency and estimated cost. Run:

```bash
python manage.py report_nutrition_label_ai --days 30
```

The report exposes total scans, resolution rate, hidden escalation rate, failed
scans, credits charged, total provider cost and average provider cost. Review it
weekly during rollout. Investigate by image cohort when escalation exceeds 20%
or resolution falls below 90%; tune preprocessing/prompt/validators before
changing the user price. Never use escalation itself as a reason to surcharge a
specific user.

## Deployment requirements

The synchronous web service needs `AI_ASSISTANT_OPENAI_API_KEY`; keeping the key
only on the async worker is insufficient. Defaults are configurable through
`NUTRITION_LABEL_AI_*`, while the commercial price remains separately configured
by `NUTRITION_LABEL_AI_CREDITS_PER_SCAN`.

Repository automation covers validation, idempotency, fixed charging, escalation,
failure release, optional image ownership and deletion. Camera optics, gallery
selection, permissions and real-label quality still require a physical iPhone
TestFlight smoke test.
