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
first native build includes `expo-dev-client` and `expo-secure-store`; JavaScript
changes after that can use the development server until native configuration
changes again.

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
- `src/design/tokens.json` is the platform-neutral visual contract consumed by
  native components.
- The CML04 execution path writes append-only meal evidence, contextualizes
  weights, freezes periodic reviews and requires explicit approval for prepared
  future revisions.
- Calendarization owns logical reminder times and upcoming events. Native local
  notification/APNs delivery and permission handling remain CML07.
- App Store signing, universal links, camera, notifications and privacy manifests
  belong to later CML patches.
