# 0184 - Exclusive native reminder delivery and iOS release capabilities

Status: accepted
Date: 2026-08-05

## Decision

`ProgramCalendarization` remains the only reminder schedule. An authenticated
iPhone registers its APNs device token against the existing OAuth device session;
the token is never an account credential and is omitted from Django Admin. The
server returns one effective mode for that device:

- `apns` only when the APNs kill switch and every provider credential are ready;
- `local` otherwise, including simulator, offline and incomplete server setup.

When APNs is active the app removes its My Scoope local requests. Otherwise it
recreates only its own local requests from the same stable event keys and UTC
instants. A device never receives both channels for one agenda. Permission denial
removes owned local requests but never blocks Today, check-ins or the program.

Sign in with Apple joins the existing allauth page used by the mobile PKCE
system-browser flow. It does not create a second native identity/token authority.
Google, Apple and email/password all end by issuing the same My Scoope OAuth code
and rotating device session.

SecureStore remains the Keychain adapter with `WHEN_UNLOCKED_THIS_DEVICE_ONLY`;
Face ID is not declared. The iOS prebuild declares only camera, Sign in with Apple
and Push Notifications. Camera frames and Vision OCR text remain on-device. The
privacy manifest contains the required-reason APIs declared by Expo/React Native
and the app's linked account, health/fitness, interaction, purchase and user-content
categories; crash data is unlinked and no data is used for tracking. Mobile Sentry
is inert without a DSN and strips user,
request, header, query, cookie, environment and breadcrumb data before transport.

## Consequences

- Direct APNs uses a cached short-lived ES256 provider token and HTTP/2; credentials are
  opt-in environment secrets and incomplete activation fails Django checks.
- APNs subscriptions disappear with their OAuth device session/account and
  inactive records follow the existing notification retention window.
- Sentry source-map upload requires EAS-only organization, project and auth-token
  secrets; these values are not committed or exposed as public runtime config.
- Repository completion cannot claim App Store signing or device QA. Expo SDK 57
  requires Xcode 26.4; that Xcode requires macOS Tahoe 26.2 or later. The current
  macOS 15.3.1/Xcode 14 host must be upgraded (or replaced by an eligible EAS/Mac
  runner) before OCR, APNs, Keychain and archive evidence can close physically.
