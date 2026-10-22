# Incident contract

Use this contract whenever an incident is created, handed off, updated, or closed.

## Priority matrix

| Priority | Definition | Response |
| --- | --- | --- |
| P0 | Privacy/security, billing, data loss, or a widespread blocker | Surface immediately, contain risk, and pause lower-priority work |
| P1 | Crash or core flow unavailable with no workaround | Investigate promptly and assign a clear owner |
| P2 | Functional or navigation failure with a usable workaround | Queue with reproducible evidence and affected scope |
| P3 | Comprehension, copy, content, portion guidance, or visual issue | Route to UX/product unless impact justifies escalation |

Severity reflects impact, not how easy the fix appears.

## Incident packet

Produce a compact record with these fields:

- **ID and title:** stable short identifier plus the user-visible symptom.
- **Status:** new, investigating, routed, fixing, verifying, resolved, duplicate, or not-actionable.
- **Priority and confidence:** P0-P3 plus high, medium, or low confidence.
- **Scope:** environment, Sentry project, release/build, platform, route, and affected cohort when known.
- **Impact:** what the tester cannot do or misunderstands and whether a workaround exists.
- **Evidence:** source, timestamp or time window, and a short redacted fact. Link to the source when available.
- **Correlation:** Sentry issue/release, support code or `mobile.api.request_id`, Render request ID, and TestFlight feedback/crash record when available.
- **Cause:** explicitly label as verified, suspected, or unknown.
- **Reproduction:** minimal deterministic steps, or why reproduction is not yet possible.
- **Owner:** mobile, backend, release, UX/product, verifier, or Felipe for a business decision.
- **Next action:** one concrete action with the expected evidence it should produce.
- **Verification:** focused test, staging smoke check, deployment health, or confirmation from the affected/newer beta build.

Never paste secrets or sensitive user payloads into the packet.

## Routing decision

Assign one primary owner. Add supporting owners only when evidence crosses a boundary.

- **Mobile:** React Native, Expo Router, navigation state, native crash, device-specific behavior, local persistence, or client request construction.
- **Backend:** Django, API response, data contract, database, server exception, latency, or authorization enforced by the service.
- **Release:** EAS, TestFlight, signing, environment configuration, source maps, build availability, or release metadata.
- **UX/product:** comprehension, terminology, content, portion guidance, expected behavior, or flow design.
- **Verifier:** independent reproduction, regression validation, or proof that a specific build contains the fix.

If ownership is ambiguous, assign the boundary where the first disproving check can be run fastest.

## Closure conditions

Mark an incident resolved only when all applicable conditions hold:

1. The cause is verified or the symptom is eliminated by a controlled change.
2. A focused regression check passes at the code boundary that changed.
3. Release or environment changes have distinct deployment evidence; repeated local tests are not deployment evidence.
4. For TestFlight-only behavior, a build containing the fix is installed and the relevant flow or crash signal is checked there.
5. Monitoring shows no recurrence for an appropriate window, or the user explicitly accepts a different closure criterion.
6. The packet records the fix version/build and remaining uncertainty.

Use `duplicate` only when the existing incident truly tracks the same user-visible symptom and affected boundary. Use `not-actionable` only when evidence demonstrates expected behavior, insufficient reproducibility after reasonable checks, or an external condition outside current scope.
