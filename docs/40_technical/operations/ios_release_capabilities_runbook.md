# iOS release capabilities runbook

Status: current
Date: 2026-10-21

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

## Physical development workflow

The Expo project is `@my-scoope/my-scoope`, with EAS project ID
`ea9b4286-222a-4b79-93da-584ed07ed072`. The Apple App ID
`com.myscoope.app` belongs to the My Scoope SpA team. Keep those identifiers
aligned with `mobile/app.json`; do not create replacement identifiers from an
Xcode Personal Team.

Register each physical test device before creating its first ad hoc build:

```bash
cd mobile
npx eas-cli@latest device:create
npx eas-cli@latest build --platform ios --profile development
```

After installing the development build, enable iOS Developer Mode and run Metro
from the same Wi-Fi network:

```bash
cd mobile
npm start -- --lan
```

The phone connects to the LAN Metro address shown by Expo. The API remains a
separate dependency: `EXPO_PUBLIC_API_BASE_URL` must be HTTPS and reachable from
the phone; `localhost` and `127.0.0.1` refer to the phone itself.

The development profiles set `SENTRY_DISABLE_AUTO_UPLOAD=true` so missing Sentry
organization/project build credentials do not block local device builds. Preview
and production builds must configure `SENTRY_ORG`, `SENTRY_PROJECT` and
`SENTRY_AUTH_TOKEN` before relying on source-map upload.

On 2026-08-20, an ad hoc Expo development build installed and opened on a physical
iPhone, and connected successfully to Metro over LAN. This proves signing,
installation and the development-server path only; it does not close the release
evidence listed below.

## Simulator staging and TestFlight production workflow

Use the iOS Simulator for feature and staging validation. The guarded commands
inject the Render staging API and reject execution from `main`:

```bash
cd mobile
npm run ios:staging
npm run start:staging
```

TestFlight is reserved for production candidates built from a clean, synchronized
`main`. Building and submitting remain separate approval points:

```bash
git switch main
git fetch origin main
git pull --ff-only
cd mobile
npm run verify:environments
npm run build:production
# Review the EAS result before continuing.
npm run submit:production
```

The `testflight-production` and default `production` profiles both resolve to
`https://www.myscoope.com`. The source guard requires `main`, a clean worktree,
the `origin/main` upstream, and equal local/upstream commits. `eas.json` also
sets `requireCommit=true`. The ambiguous `testflight` profile was removed so a
store build cannot silently keep the staging API URL, and automatic submission
is intentionally absent from the package command.

Before the first production build, verify in Render that the `my-scoope`
production service is connected to GitHub branch `main`. `render.yaml` defines
the service and deployment commands but does not prove the externally selected
branch. Treat this dashboard check as a release gate.

Historical note: on 2026-08-21, EAS build `1.0.0 (3)` was uploaded to App Store Connect, assigned
to the internal `Team (Expo)` group, installed from TestFlight on a physical
iPhone and connected successfully to `https://myscoope-staging.onrender.com`.
That legacy build proves signing and installation only. New TestFlight builds
must use the production workflow above; staging validation now belongs to the
simulator. It used App Store Connect app ID `6804048394`, bundle ID
`com.myscoope.app`, production APNs entitlements and EAS-managed signing
credentials.

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

Set `EXPO_PUBLIC_SENTRY_DSN` only for builds that should report crashes. In both
the EAS `preview` and `production` environments, configure `SENTRY_ORG`,
`SENTRY_PROJECT`, sensitive `SENTRY_AUTH_TOKEN`, and the public DSN. Never prefix
the three build credentials with `EXPO_PUBLIC_`. Release profiles publish source
maps to EAS and Sentry; the EAS post-install guard fails the build when any of
these values is absent. Development and simulator profiles deliberately keep
automatic upload disabled.

During the small external beta, release profiles use
`EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=1` so every navigation transaction is
eligible for capture. Reduce this to the normal production rate (`0.05`) before
public App Store distribution, after beta evidence has closed the navigation
risks. Error capture is not sampled.

Trigger one non-sensitive test crash and verify all of the following before
assigning the build to external testers:

- the event is symbolicated to repository files and lines;
- environment, app version, build and release identify the exact binary;
- the navigation trail uses route templates such as `/program/days/[id]`;
- API breadcrumbs retain only normalized path, method, outcome, status, duration,
  response size, error code and the safe request correlation ID;
- the event contains no user object, request body, cookies, headers, query string,
  OCR/nutrition content, screenshot, view hierarchy or arbitrary breadcrumb data.

Create Sentry alerts for new issues, regressions and fatal/error spikes. Route
backend `5xx` and mobile API contract failures to the same operational inbox.
Do not enable Session Replay or automatic screenshots during beta.

## External beta incident routine

Keep tester feedback enabled for the TestFlight group. For each report, record
build, device, iOS version, local timestamp/timezone, starting screen, actions,
expected result, actual result, frequency, network condition and an optional
TestFlight screenshot. Do not ask testers to paste nutrition, authentication,
receipt or payment payloads.

Triage reports using these categories:

- `P0`: privacy, security, billing, data loss or a complete blocker;
- `P1`: crash or broken core flow without a practical workaround;
- `P2`: functional/navigation problem with a workaround;
- `P3`: comprehension, copy, content or visual refinement.

For crashes, begin with TestFlight/App Store Connect and the matching Sentry
release. For non-crashing functional problems, use the Sentry route/API trail.
When the app displays a `Código de soporte`, search that value in Sentry under
`mobile.api.request_id` and in Render as the HTTP `requestID`/`Rndr-Id`. Render
and My Scoope return the same opaque correlation value as `X-Request-ID` to the
mobile client; it contains no user or request payload.

During active external beta, review TestFlight feedback, Sentry new/regressed
issues and Render `5xx` once each working day. Create one issue per distinct
symptom, reproduce it, add a regression test where the behavior is representable,
and close it only after verification in a newer TestFlight build. Avoid creating
duplicate issues for multiple testers who encountered the same signature.

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
