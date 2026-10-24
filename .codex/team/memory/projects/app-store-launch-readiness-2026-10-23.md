# App Store Launch Readiness — 2026-10-23

Status: blocked
Review type: cross-functional readiness snapshot
Sponsor and decision owner: Felipe Dides
Coordination: AI Team Capability Steward

## Decision supported

Determine what remains before My Scoope can be submitted to App Review and launched
publicly as a useful, reliable, observable, and financially controlled consumer iOS
product.

## Current recommendation

Do not submit the current candidate to App Review. Continue with a controlled beta
after closing the active P1 and the technical beta gates. Reassess public launch on
one exact candidate commit and build after the required evidence below is attached.

This snapshot distinguishes Apple submission requirements, operational safety, and
business readiness. A business-readiness item is not presented as an Apple rule.

## Verified strengths

- EAS build `1.0.0 (43)`, commit `e3ead957...`, the production Render deploy, and
  the Sentry release are correlated.
- The consumer outcome, MVP boundary, Free/Basic/Pro offer, localized store copy,
  privacy-label draft, reviewer notes, and physical release matrix are defined.
- Mobile Sentry, backend Sentry, TestFlight/EAS, and Render supplied live read-only
  evidence during this review.
- Repository documentation correctly distinguishes repository completion from
  physical, deployed, and App Store evidence.

## Hard blockers before App Review

| Gate | State | Evidence and closure |
| --- | --- | --- |
| `/api/v1/home` production 500 | blocked | Sentry mobile `MOBILE-1` and backend `PYTHON-DJANGO-17` correlate the failure on build 43. Promote the staged fix, run the required gate on the exact commit, smoke with an account containing a weight record, and observe no recurrence. |
| Recent native crashes | blocked | TestFlight reports two build-42 crashes in meal editing and food selection. Reproduce the same scenarios on build 43 or its successor and verify no matching TestFlight/Sentry event. |
| Physical iOS matrix | not evaluated | Complete Apple login/revocation, Keychain, camera/OCR, APNs/local fallback, StoreKit sandbox, deletion, privacy/archive inspection, and one sanitized symbolicated crash on the exact candidate. See `docs/40_technical/operations/ios_release_capabilities_runbook.md`. |
| App Store Connect package | not evaluated | Verify agreements, tax/banking, subscription products and notifications, age rating, App Privacy, legal/support URLs, demo account, screenshots, reviewer information, and submission state. See `docs/40_technical/operations/cml08_app_store_review_runbook.md`. |
| Observability closure | at risk | Confirm alerts for new issues, regressions, and fatal/error spikes; verify a sanitized crash payload; lower the public tracing sample rate from the beta value to the production value defined by the runbook. |
| Screenshots | at risk | The manifest currently contains five shots while the internal runbook asks for six. Resolve the intended package and confirm accepted slots and dimensions in App Store Connect. |

## Operational safety gates before public launch

| Gate | State | Evidence and closure |
| --- | --- | --- |
| Render topology and deploy contract | blocked | Live production differs materially from `render.yaml` and the production runbook: migrations run during build, no configured health-check path was observed, and declared notification/housekeeping services were absent. Reconcile the environment or record an explicit authoritative exception, then verify deployment and health. |
| Data recovery | not evaluated | No accessible dated restore drill proves recovery and invariants. Complete the isolated restore procedure from the PostgreSQL backup/restore runbook. |
| Database exposure | at risk | Live PostgreSQL metadata reported `0.0.0.0/0`. Inventory legitimate consumers, restrict access where possible, and verify connectivity. |

## Business readiness gates for a controlled public launch

| Gate | State | Evidence and closure |
| --- | --- | --- |
| Activation and customer value | blocked | Run a bounded cohort through signup → onboarding → first plan → calendar/Today → first check-in → first weight. Record success, abandonment, comprehension, and the explicit decision for first-plan continuity. |
| Launch measurement | blocked | Define and prove the minimum funnel from acquisition to first value and conversion. Advanced cohort/LTV analysis can follow later. |
| Commercial launch brief | at risk | Approve the initial segment, promise, offer, channel, objections, attributable experiment, and stop/scale rules. |
| Financial operating envelope | not evaluated | Build a sourced base/downside/upside model with fixed and variable cost, AI usage, Apple economics, support, budget ceiling, runway, and stop/scale rules. |
| Accounting for Apple revenue | blocked if monetization ships | Obtain Chile-specific professional criteria and define the authorized register, commissions, refunds, settlements, currencies, reconciliation, and exceptions. The first real payout reconciliation can occur after launch; the policy and procedure cannot. |

If My Scoope considers a Free-only first release, removal of paid subscriptions must
be an explicit product and App Store scope decision. Do not silently treat missing
billing evidence as resolved.

## Recommended order

1. Select one candidate commit and close the `/api/v1/home` P1 in production.
2. Verify the two recent native crashes and observability alert/privacy behavior.
3. Reconcile Render, restrict database access, and prove restore capability.
4. Execute the complete physical matrix on the candidate build.
5. Complete and independently verify the App Store Connect package.
6. Run the bounded customer/activation cohort with the minimum launch funnel.
7. Approve the commercial brief, financial envelope, and accounting procedure.
8. Hold a final verifier-led go/no-go review against the exact build and production
   deployment.

## Source coverage and limits

Checked: repository sources, mobile and backend Sentry, TestFlight/EAS build and
crash context, and Render service/deploy metadata.

Not verified: App Store Connect configuration and submission, build logs, full
physical matrix, legal/accounting approval, restore drill, exact CI evidence for
the staged backend fix, and direct customer research evidence.

The audited local checkout was dirty and behind `origin/staging`; local worktree
state is not release evidence. This snapshot must be refreshed against the exact
integrated candidate before a launch decision.
