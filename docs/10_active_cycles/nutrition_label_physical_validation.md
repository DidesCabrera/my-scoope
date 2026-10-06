# Nutrition-label physical validation worksheet

Status: active
Date: 2026-10-06

## Build identity

- Git commit:
- TestFlight build:
- API environment:
- iPhone model:
- iOS version:
- Tester:
- Date:

Do not reuse observations from a different commit or build. Run the internal
nutrition-label AI report after the matrix to reconcile escalation and charges.

## Required matrix

Record at least 30 real labels. Include Spanish and English, per-100-g,
per-serving, per-100-ml, dual-column, decimal comma/point, kcal/kJ, sodium mg/g,
small type, glossy and matte surfaces, flat and curved packages, normal and low
light, cropped bases, deliberate blur and non-label controls.

| # | Language/basis | Package/light | Camera/gallery | Local quality | Repeated | Usable before edits | Fields edited | Primary/escalated/failed | Credits | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | |
| 2 | | | | | | | | | | |
| 3 | | | | | | | | | | |
| 4 | | | | | | | | | | |
| 5 | | | | | | | | | | |
| 6 | | | | | | | | | | |
| 7 | | | | | | | | | | |
| 8 | | | | | | | | | | |
| 9 | | | | | | | | | | |
| 10 | | | | | | | | | | |
| 11 | | | | | | | | | | |
| 12 | | | | | | | | | | |
| 13 | | | | | | | | | | |
| 14 | | | | | | | | | | |
| 15 | | | | | | | | | | |
| 16 | | | | | | | | | | |
| 17 | | | | | | | | | | |
| 18 | | | | | | | | | | |
| 19 | | | | | | | | | | |
| 20 | | | | | | | | | | |
| 21 | | | | | | | | | | |
| 22 | | | | | | | | | | |
| 23 | | | | | | | | | | |
| 24 | | | | | | | | | | |
| 25 | | | | | | | | | | |
| 26 | | | | | | | | | | |
| 27 | | | | | | | | | | |
| 28 | | | | | | | | | | |
| 29 | | | | | | | | | | |
| 30 | | | | | | | | | | |

## Required controls

- At least two deliberately blurred images must be blocked locally.
- At least one dark and one overexposed image must be blocked or warned locally.
- At least two non-label images must not produce a saved food.
- Reject one clear preview and confirm that credits remain unchanged.
- Double-tap capture and confirm that only one photo is created.
- Retry the same accepted image after a simulated recoverable network failure and
  confirm that no duplicate provider call or charge is created.
- Capture the same label through camera and gallery and compare normalized output.

## Closure calculations

- Legible labels tested:
- Usable before edits:
- Usable-result rate:
- Locally rejected controls:
- False local rejections:
- Escalated scans:
- Escalation rate:
- Total successful charges:
- Duplicate charges:
- Unresolved scans charged:

## Pass criteria

- usable-result rate is at least 90%;
- every deliberately unreadable/non-label control fails closed;
- rejected previews and unresolved analyses charge zero credits;
- there are no duplicate captures or charges;
- every saved result was explicitly reviewed;
- no reproducible focus lock remains;
- escalation stays below 20% or has a documented corrective investigation.
