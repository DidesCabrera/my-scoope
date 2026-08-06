# iOS release capabilities runbook

Status: current
Date: 2026-08-05

## Host and signing prerequisites

1. Upgrade the build host to macOS Tahoe 26.2 or later and install Xcode 26.4+
   (Expo SDK 57 requirement). Select that developer directory and accept the Xcode
   license/components.
2. Keep CocoaPods installed, then run production prebuild with
   `EXPO_PUBLIC_APNS_ENVIRONMENT=production npx expo prebuild --platform ios --clean`
   or use an EAS production build.
3. In Apple Developer, register `com.myscoope.app`, enable Push Notifications and
   Sign in with Apple, and create development plus distribution provisioning
   credentials. EAS may manage certificates/profiles, but must not invent the
   bundle identifier or Apple team.
4. Create/associate the App Store Connect application. Signing, agreements and
   account roles are external gates; no identifier in source proves they exist.

## Sign in with Apple

Create a web Service ID associated with the primary App ID and allow each exact
HTTPS return URL, for example:

```text
https://staging.example.com/accounts/apple/login/callback/
https://www.myscoope.com/accounts/apple/login/callback/
```

Create an allauth `SocialApp` for provider `apple` on the correct Django `Site`:

- `client_id`: Apple Service ID (comma-separated IDs only if intentionally used);
- `secret`: Apple Sign in key ID;
- `key`: Apple Team ID;
- `settings.certificate_key`: complete `.p8` private key.

Verify Apple, Google and email/password all resume the original `/oauth/authorize`
request and issue the same mobile PKCE authorization-code contract. Test both
Apple's real email and Hide My Email. Revocation/deletion handling remains part of
the physical review gate.

## APNs and reminders

Create an APNs-capable `.p8` key and set the `MYSCOOPE_APNS_*` values documented
in the notification runbook on both the API and notification worker. Keep the
kill switch false until sandbox device registration and one idempotent delivery
pass. Test local fallback first, then APNs; inspect that switching to APNs removes
owned local requests and does not duplicate an alert.

## Sentry

Set `EXPO_PUBLIC_SENTRY_DSN` only for builds that should report crashes. Configure
`SENTRY_ORG`, `SENTRY_PROJECT` and sensitive `SENTRY_AUTH_TOKEN` in EAS/build
secrets for source maps; never prefix those build credentials with `EXPO_PUBLIC_`.
Trigger one non-sensitive test crash and verify symbolication. Confirm the event
contains no user object, request body, cookies, headers, query string, environment
payload or breadcrumb data.

## Physical release evidence

On the signed TestFlight build and a real iPhone:

- Apple login, logout, token rotation and account deletion/revocation;
- Keychain session restore after app termination and expected loss after uninstall;
- camera permission denial/grant and Apple Vision OCR with several real labels;
- confirmation that the image/raw OCR text never reaches API/Sentry;
- local reminder fallback, APNs production token/delivery, tap navigation and no
  duplicate channel;
- StoreKit sandbox purchase/restore/lifecycle from CML06;
- privacy manifest/archive inspection against actual collection plus App Store
  privacy labels, and one symbolicated sanitized crash.

Record device/iOS/build numbers and screenshots/log timestamps without account or
nutrition PII. CML07 physical closure requires this evidence; CML08 then owns
privacy labels, metadata, screenshots, reviewer notes and TestFlight review.
