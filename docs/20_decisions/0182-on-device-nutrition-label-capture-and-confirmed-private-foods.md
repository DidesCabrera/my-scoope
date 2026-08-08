# 0182 - On-device nutrition-label capture and confirmed private foods

Status: accepted
Date: 2026-08-05

## Decision

Nutrition-label OCR runs on the consumer's iPhone. `expo-camera` captures a
temporary image and a local Expo module uses Apple Vision text recognition. The
photo and raw recognized text are not uploaded to My Scoope. React Native
normalizes likely values into the existing per-100-gram food contract and makes
every result editable before persistence.

OCR is assistive evidence, never an authority. The client exposes missing,
low-confidence, basis-conversion and calorie/macro-consistency warnings. It may
fall back to the same manual review form when camera permission is denied, the
camera is unavailable or the native OCR module is absent.

Only explicit confirmation calls the consumer API. The server validates the
normalized fields, checks the existing food-creation entitlement and creates an
unverified, solver-disabled, non-global `notas.Food` owned by that user. The same
transaction creates an idempotent `FoodLabelCaptureReceipt` containing the OCR
engine, basis, confidence summary, warnings and a hash of the confirmed payload.
It never stores the photo or raw OCR text.

## Consequences

- A capture abandoned before confirmation leaves no server-side food or receipt.
- Retried confirmations cannot create duplicates or silently change values.
- Captured foods are private operational foods; they are never promoted into the
  global or master catalog automatically.
- Barcode lookup remains outside the consumer MVP.
- The native module is iOS-only because Android is deferred. CML07 still owns
  physical-device permission copy, privacy-manifest and App Store capability QA;
  it does not redesign the CML05 capture contract.
