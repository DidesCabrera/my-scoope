# 0191 - AI nutrition-label extraction with internal model escalation

Status: accepted
Date: 2026-09-03
Supersedes: 0182 for automatic label extraction and image handling

## Decision

My Scoope uses external multimodal AI to extract nutrition labels captured from
camera or gallery. Apple Vision remains an optional device-side comparison signal,
not the final extraction authority. The user must explicitly authorize temporary
image processing and review every normalized value before a private food is saved.

The commercial unit is a fixed, configurable number of credits per successful
scan. My Scoope first uses Luna and automatically escalates to Sol when deterministic
quality checks require it. Escalation is invisible, never changes the user charge
and its incremental provider cost is absorbed internally. Unresolved scans are not
charged.

Original images and raw provider/OCR output are never persisted. A user may opt in
to retain only the bounded, re-encoded image that was analyzed; it remains private,
owner-readable and independently deletable.

## Consequences

- Free, Basic and Pro use their common credit wallet instead of separate scan quotas.
- Provider/model routing can evolve without changing the user-facing product.
- `FoodLabelAIAnalysis` measures the exact percentage and cost of escalated scans.
- `AIUsageEvent` preserves per-call model, token, latency and cost observability.
- A provider outage or illegible image releases the reserved credits.
- The manual food form remains the no-AI fallback.
- The privacy disclosure version changes and existing mobile users must accept it.
- Retained images use bounded database storage for the initial release; private
  object storage is the planned scale boundary, not a prerequisite for rollout.
