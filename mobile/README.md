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

## Mobile environments

Development and release environments are intentionally asymmetric:

- the iOS Simulator runs the current `staging` or feature-branch code against
  `https://myscoope-staging.onrender.com`;
- TestFlight is reserved for committed `main` code against
  `https://www.myscoope.com`.

Start or rebuild the staging simulator with the guarded commands:

```bash
cd mobile
npm run ios:staging     # only when the native simulator build must change
npm run start:staging   # normal Metro development loop
```

The simulator command is rejected from `main`. Feature branches based on
`staging` are allowed so changes can be tested before merging.

Production build and submission are deliberately separate operations:

```bash
git switch main
git fetch origin main
git pull --ff-only
cd mobile
npm run verify:environments
npm run build:production
# After reviewing the completed EAS build:
npm run submit:production
```

The production guard requires `main`, a clean worktree, the `origin/main`
upstream, and identical local/upstream commits. EAS also requires committed
source. The old ambiguous `testflight` profile no longer exists, and neither
production command uses `--auto-submit`.

Before the first production build, confirm in the Render dashboard that the
`my-scoope` production service deploys from GitHub branch `main`. The repository
declares the production service but its selected branch is owned by Render's
external service configuration.

`MYSCOOPE_BUILD_TARGET` and `EXPO_PUBLIC_DEPLOYMENT_ENV` must agree with the API
URL. Both dynamic Expo configuration and runtime application configuration fail
closed if staging and production are mixed.

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
- `http://localhost:8081/dev/ui-gallery` is the internal Expo component gallery
  during local web development. It is linked from Account only in development
  builds and redirects away in production. The mobile contract tests fail if its
  route guard or entry point disappears.
- The CML04 execution path writes append-only meal evidence, contextualizes
  weights, freezes periodic reviews and requires explicit approval for prepared
  future revisions.
- Calendarization owns logical reminder times and upcoming events. CML07 selects
  APNs or deterministic local delivery per iPhone and never schedules both modes.
- `Mi programa` activates an owned Program, displays its immutable dated snapshots
  and delegates pause, resume and cancel to the versioned consumer API. Replacing
  an active program and accepting empty days always require explicit confirmation.
- `Propuestas` renders a bounded server projection and server-authorized actions.
  Approval and application are separate confirmations; external-subject PPK
  warnings require acknowledgement, and an applied result links to its trusted
  Meal or DailyPlan library detail.
- `Comparador` follows the web slot model for owned Foods, Meals and DailyPlans:
  two initial positions, explicit add/remove and repeated entities when useful.
  Food quantities are edited in grams with the established 100 g fallback;
  non-Food comparisons reject quantities. Results are grouped by metric with
  server-computed relative bars. Saved detail renders a frozen snapshot, while
  explicit edit/save refreshes it from current source values.
- `Asistente AI` lists persisted owner-scoped conversations and supports new or
  resumed chats over the durable submit/poll API. A pending server job is recovered
  when its route is reopened, one turn is allowed per conversation, and completed
  jobs trigger a trusted chat-detail refresh instead of exposing raw conversation
  or provider payloads. MCE06 renders a bounded typed card union and keeps all
  prepared mutations behind an explicit trusted confirmation.
- CML05 keeps label photos and raw OCR text on-device, exposes uncertain fields
  for editing and persists only explicitly confirmed private foods.
- CML06 fetches localized App Store prices, passes the server-issued
  `appAccountToken`, verifies signed transactions before finishing them, restores
  purchases and opens native subscription management. Product identifiers and
  prices must first be configured in App Store Connect and `BillingProduct`.
- App Store signing and physical camera/OCR, Apple login, APNs, Keychain and crash
  proof remain CML07 external gates; metadata, screenshots and review belong CML08.
