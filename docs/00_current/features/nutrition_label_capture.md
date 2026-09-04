# Nutrition-label capture

Status: current
Date: 2026-08-05

## Product contract

The consumer mobile app can point the iPhone camera at a nutrition table and
turn it into a private operational food. The path is deliberately review-first:

```text
temporary camera image
  -> Apple Vision OCR on device
  -> client-side normalization candidate
  -> editable review with uncertainty
  -> explicit confirmation
  -> private notas.Food + capture receipt
```

No server request occurs during capture or OCR. The temporary photo is deleted
from the app cache after recognition, and raw recognized text is not sent or
persisted. If camera access is denied or OCR is unavailable, the user can still
enter and review the same fields manually.

## Normalization and review

The client recognizes Spanish and English nutrient labels, decimal comma/point,
values per 100 g, values per serving and common dual-column tables. Per-serving
values are converted to the operational per-100-gram contract only when a serving
weight is available. Common unit-based portions such as `1 unidad (30 g)` are
supported. If the OCR cannot recover the serving weight, the raw per-serving
readings are kept separate: the review flow requires the user to enter the weight
and performs the conversion before the food form can be confirmed.

The review screen exposes:

- protein, carbohydrate and fat as required confirmed fields;
- declared energy, saturated fat, sugar, fiber, sodium and serving weight when
  available;
- missing or low-confidence fields;
- conversion-basis warnings;
- a warning when declared energy materially differs from macro-derived energy.

The user may edit every value. OCR never persists or approves a food by itself.

## Persistence and safety

`POST /api/v1/foods/label-captures` accepts only confirmed normalized values and
technical confidence metadata. It requires `mobile:write`, the existing
`can_create_food` entitlement and an idempotency key. A payload that declares a
per-serving source without a serving weight is rejected as a second fail-closed
guard even if it does not come from the current mobile client.

The application service creates a user-owned `notas.Food` with `is_global=false`,
`is_verified=false` and `solver_enabled=false`. A one-to-one
`FoodLabelCaptureReceipt` stores provenance, warnings and a confirmed-payload
hash without raw OCR text or an image. Account deletion removes the food and its
dependent receipt.

## Native boundary

The iOS module lives at `mobile/modules/nutrition-label-ocr/`, is auto-linked by
Expo Modules API and uses Apple Vision without a remote OCR provider. The camera
uses continuous autofocus for small label text, offers a torch control, uses an
explicit Spanish purpose string, disables microphone recording and disables
barcode support. Apple Vision receives a bounded nutrition vocabulary to improve
recognition of the supported Spanish fields. Android and barcode lookup remain
deferred.

Repository checks validate autolinking, TypeScript, normalization and the web
fallback. The native module also compiles as part of the iOS application. A
physical iPhone and a real label are still required to exercise camera optics and
approve final permission/privacy copy during CML07.
