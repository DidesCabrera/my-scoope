import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const comparator = readFileSync(new URL("../src/app/comparator/index.tsx", import.meta.url), "utf8");
const listScreen = readFileSync(new URL("../src/components/libraries/library-list-screen.tsx", import.meta.url), "utf8");
const limitModel = readFileSync(new URL("../src/components/subscriptions/commercial-limit.ts", import.meta.url), "utf8");
const limitSheet = readFileSync(new URL("../src/components/subscriptions/commercial-limit-sheet.tsx", import.meta.url), "utf8");

test("the library create action checks current entitlements before asking for a name", () => {
  assert.match(listScreen, /apiRequest<EntitlementsData>\("\/api\/v1\/entitlements", \{ cache: "no-store" \}\)/);
  assert.match(listScreen, /reachedCommercialLimit\(entitlements, entity\)/);
  assert.match(listScreen, /setCommercialLimit\(reachedLimit\)/);
  assert.match(listScreen, /onPress: \(\) => void openCreate\(\)/);
});

test("all four commercial entities use the backend entitlement keys", () => {
  assert.match(limitModel, /comparison: \{ error: "max_saved_comparisons_reached", limit: "max_saved_comparisons", usage: "comparison" \}/);
  assert.match(limitModel, /dailyPlan: \{ error: "max_dailyplans_reached", limit: "max_dailyplans", usage: "dailyplan" \}/);
  assert.match(limitModel, /meal: \{ error: "max_meals_reached", limit: "max_meals", usage: "meal" \}/);
  assert.match(limitModel, /program: \{ error: "max_programs_reached", limit: "max_programs", usage: "program" \}/);
});

test("saving a new comparison performs a preflight and handles a server-side race", () => {
  assert.match(comparator, /if \(!savedId\) \{[\s\S]*reachedCommercialLimit\(entitlements, "comparison"\)/);
  assert.match(comparator, /isCommercialLimitError\(nextError, "comparison"\)/);
  assert.match(comparator, /<CommercialLimitSheet \{\.\.\.commercialLimit\}/);
});

test("the limit popup keeps existing content safe and offers the subscriptions route", () => {
  assert.match(limitSheet, /Tu contenido actual sigue disponible/);
  assert.match(limitSheet, /Ver planes disponibles/);
  assert.match(listScreen, /router\.push\("\/subscription"\)/);
  assert.match(comparator, /router\.push\("\/subscription"\)/);
});
