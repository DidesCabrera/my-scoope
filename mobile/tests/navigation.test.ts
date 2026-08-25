import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { listAvailableProductAreas, productAreas } from "../src/navigation/product-areas";

test("the consumer navigation catalog includes every MCE product area", () => {
  assert.deepEqual(productAreas.map((area) => area.key), [
    "home",
    "program",
    "assistant",
    "proposals",
    "comparator",
  ]);
});

test("only product areas with a functional route are exposed in the sidebar", () => {
  const available = listAvailableProductAreas();
  assert.deepEqual(available.map((area) => area.key), ["home", "program", "assistant", "proposals", "comparator"]);
  assert.ok(available.every((area) => String(area.href).startsWith("/")));
});

test("MCE07 product journeys have native destinations and refocus refreshes", async () => {
  const proposal = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id].tsx"), "utf8");
  const comparison = await readFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  const program = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  const programDay = await readFile(path.resolve(process.cwd(), "src/app/program/days/[id].tsx"), "utf8");
  const today = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  const account = await readFile(path.resolve(process.cwd(), "src/app/account.tsx"), "utf8");
  assert.match(proposal, /\/libraries\/meals\//);
  assert.match(proposal, /\/libraries\/daily-plans\//);
  assert.match(comparison, /Usar en el Asistente/);
  assert.match(comparison, /comparisonId/);
  assert.doesNotMatch(program, /Abrir plan de hoy/);
  assert.match(program, /CalendarizedProgramPlanning/);
  assert.match(programDay, /<EntityDetailPage/);
  assert.match(programDay, /title="Tabla de comparación entre comidas"/);
  assert.match(programDay, /title="Detalle de cada Comida"/);
  assert.match(programDay, /<NutritionEntityCard/);
  assert.match(programDay, /calendarizedDayId=\$\{dayId\}&mealKey=/);
  assert.match(programDay, /<ChevronRight/);
  assert.match(programDay, /mode: "library-detail", entity: "dailyPlan"/);
  assert.match(today, /\/program/);
  assert.doesNotMatch(today, /check-in/);
  assert.doesNotMatch(today, /Mi suscripción|Cuenta, privacidad y ayuda|Configurar recordatorios/);
  assert.match(account, /label="Mi suscripción"/);
  assert.match(account, /router\.push\("\/subscription" as Href\)/);
  for (const screen of [proposal, comparison, program, programDay, today]) assert.match(screen, /useFocusEffect/);
});

test("shared screens use compact scroll identities and only Home keeps the centered logo", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const entityIdentity = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-entity-identity.tsx"), "utf8");
  const libraryList = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const primitives = await readFile(path.resolve(process.cwd(), "src/components/ui/primitives.tsx"), "utf8");
  const headerBody = navigation.slice(navigation.indexOf("export function AppNavigationHeader"), navigation.indexOf("export function useHeaderPresentation"));
  assert.match(headerBody, /isHome \? <View pointerEvents="none" style=\{styles\.headerLogo\}><MyScoopeLogo/);
  assert.match(headerBody, /HeaderIdentity/);
  assert.match(headerBody, /defaultIdentityVisible/);
  assert.match(navigation, /Icon color=\{tokens\.color\.textMain\}/);
  assert.match(entityIdentity, /<EntityIcon entity=\{entity\} size="header" \/>/);
  assert.doesNotMatch(entityIdentity, /tone="white"/);
  assert.match(primitives, /contentOffset\.y > 1/);
  assert.match(primitives, /identityVisible: compactHeaderVisible/);
  assert.match(libraryList, /stickyHeaderIndices=\{\[1\]\}/);
  assert.match(libraryList, /contentOffset\.y >= searchOffset\.current/);
  assert.match(libraryList, /stickySearch: \{ backgroundColor: tokens\.color\.surfaceApp, borderBottomColor: "transparent", borderBottomWidth: 1/);
  assert.match(libraryList, /stickySearchPinned: \{ borderBottomColor: tokens\.color\.borderDefault \}/);
});
