# My Scoope mobile

Consumer-first React Native client for the daily My Scoope execution journey.
It uses Expo SDK 57, Expo Router, TypeScript and an Expo development build.

## Local setup

Requirements:

- Node.js 22.13 or newer;
- Xcode 26.4 or newer for the iOS SDK 57 build;
- a mobile OAuth public client registered in the target Django environment.

```bash
cp .env.example .env.local
npm ci
npm start
```

Use `npm run ios` to generate and compile the native iOS development build. The
first native build includes `expo-dev-client`, `expo-secure-store`, `expo-camera`,
`expo-iap` and the local Apple Vision OCR module. JavaScript changes after that can use the
development server until native configuration changes again.

For a physical device, `EXPO_PUBLIC_API_BASE_URL` must be an HTTPS environment
reachable by that device. The OAuth client must allow the exact value of
`EXPO_PUBLIC_OAUTH_REDIRECT_URI`.

## Checks

```bash
npm run check
```

This runs lint, strict TypeScript, session/contract tests and a production-like
web bundle as a platform-independent Metro verification. CI uses the same
commands through `scripts/ci_mobile_checks.sh`.

## Boundaries

- Django remains the authority for profiles, programs, foods, AI, weights and
  commercial state.
- Access and rotating refresh tokens are stored through SecureStore on native
  devices. No OAuth client secret exists in the app.
- `../design/ui-contract.json` is the platform-neutral visual contract. Running
  `npm run generate:ui` at the repository root derives the Django CSS variables
  and `src/generated/ui-tokens.ts`; native code imports the stable facade
  `src/design/tokens.ts`.
- `/dev/ui-gallery` is the internal Expo component gallery. It is linked from
  Account only in development builds and redirects away in production.
- The CML04 execution path writes append-only meal evidence, contextualizes
  weights, freezes periodic reviews and requires explicit approval for prepared
  future revisions.
- Calendarization owns logical reminder times and upcoming events. CML07 selects
  APNs or deterministic local delivery per iPhone and never schedules both modes.
- CML05 keeps label photos and raw OCR text on-device, exposes uncertain fields
  for editing and persists only explicitly confirmed private foods.
- CML06 fetches localized App Store prices, passes the server-issued
  `appAccountToken`, verifies signed transactions before finishing them, restores
  purchases and opens native subscription management. Product identifiers and
  prices must first be configured in App Store Connect and `BillingProduct`.
- App Store signing and physical camera/OCR, Apple login, APNs, Keychain and crash
  proof remain CML07 external gates; metadata, screenshots and review belong CML08.
