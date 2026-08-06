# CML08 App Store review runbook

## Repository-ready package

- Versioned disclosure acceptance gates every authenticated consumer before onboarding or Today.
- Account exposes privacy, terms, support, content reporting and in-app account deletion.
- `mobile/store/` is the reviewed source for localized metadata, privacy labels, TestFlight copy, screenshots and reviewer notes.
- `prepare_app_review_demo` creates a repeatable program for an existing reviewer account without storing credentials.

## External gates (do not mark complete from repository evidence)

1. Owner/legal review the published privacy policy, terms and Chile/launch-market wording.
2. Publish the production legal/support URLs and verify them without authentication.
3. Configure App Store Connect contracts, tax/banking, subscription group, products and server notifications.
4. Create a dedicated reviewer account, store its credentials only in App Store Connect, then prepare its demo program.
5. Run the CML07 physical-device matrix on the release candidate.
6. Capture all six screenshots from the same approved build and verify accepted pixel dimensions.
7. Upload an internal TestFlight build; complete smoke, purchase/restore, deletion and crash-symbol checks.
8. Invite external testers only after internal sign-off and Beta App Review information is complete.
9. Reconcile App Privacy answers against the release binary and every included SDK immediately before submission.
10. Submit the first subscription products together with the app version and paste the final reviewer notes.

## Evidence record

Record build number, commit SHA, TestFlight group, device/OS, tester, result, privacy-label reviewer, legal approval, screenshot filenames and App Review submission ID. Never record passwords, API keys, APNs keys or StoreKit credentials.
