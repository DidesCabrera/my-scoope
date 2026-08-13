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
  const today = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  assert.match(proposal, /\/libraries\/meals\//);
  assert.match(proposal, /\/libraries\/daily-plans\//);
  assert.match(comparison, /Usar en el Asistente/);
  assert.match(comparison, /comparisonId/);
  assert.match(program, /\/today/);
  assert.match(today, /\/program/);
  for (const screen of [proposal, comparison, program, today]) assert.match(screen, /useFocusEffect/);
});

test("shared screens use compact white scroll identities and only Home keeps the centered logo", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const primitives = await readFile(path.resolve(process.cwd(), "src/components/ui/primitives.tsx"), "utf8");
  const headerBody = navigation.slice(navigation.indexOf("export function AppNavigationHeader"), navigation.indexOf("export function useHeaderPresentation"));
  assert.match(headerBody, /isHome \? <View pointerEvents="none" style=\{styles\.headerLogo\}><MyScoopeLogo/);
  assert.match(headerBody, /HeaderIdentity/);
  assert.match(headerBody, /defaultIdentityVisible/);
  assert.match(navigation, /Icon color=\{tokens\.color\.textMain\}/);
  assert.match(primitives, /contentOffset\.y > 1/);
  assert.match(primitives, /identityVisible: compactHeaderVisible/);
});
