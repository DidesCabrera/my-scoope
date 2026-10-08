# CML08 App Store review runbook

## Repository-ready package

- Versioned disclosure acceptance gates every authenticated consumer before onboarding or Today.
- Suscripciones y Bolsas expone privacidad, términos y reembolsos; Cuenta conserva soporte, reporte de contenido y eliminación dentro de la app.
- `mobile/store/` is the reviewed source for localized metadata, privacy labels, TestFlight copy, screenshots and reviewer notes.
- `prepare_app_review_demo` creates a repeatable program for an existing reviewer account without storing credentials.

## External gates (do not mark complete from repository evidence)

1. Owner/legal review the published privacy policy, terms and Chile/launch-market wording.
2. Publish the production legal/support URLs and verify them without authentication.
3. Configure App Store Connect contracts, tax/banking, subscription group, products and server notifications.
4. Create `appreview@myscoope.com` through the normal production signup flow, verify it, leave MFA disabled and ensure it has no active subscription. Store its unique password only in the password manager and App Store Connect, then run `python manage.py prepare_app_review_demo --login appreview@myscoope.com` against production.
5. Configure `MYSCOOPE_APPLE_TEAM_ID` on the production web service and verify that `https://www.myscoope.com/.well-known/apple-app-site-association` returns HTTP 200 with the production Team ID and `com.myscoope.app`.
6. Run the CML07 physical-device matrix on the release candidate.
7. Capture all six screenshots from the same approved build and verify accepted pixel dimensions.
8. Upload an internal TestFlight build; complete smoke, purchase/restore, deletion and crash-symbol checks.
9. Invite external testers only after internal sign-off and Beta App Review information is complete.
10. Reconcile App Privacy answers against the release binary and every included SDK immediately before submission.
11. Submit the first subscription products together with the app version and paste the final reviewer notes.

## Evidence record

Record build number, commit SHA, TestFlight group, device/OS, tester, result, privacy-label reviewer, legal approval, screenshot filenames and App Review submission ID. Never record passwords, API keys, APNs keys or StoreKit credentials.
