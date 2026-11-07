import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { consumeSupplementIntakeSelection, stageSupplementIntakeSelection } from "../src/components/supplements/supplement-intake-selection-handoff";
import { consumePresetSupplementSelection, stagePresetSupplementSelection } from "../src/components/supplements/supplement-intake-preset-selection-handoff";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("supplement intake selection is handed back once to the matching intake", () => {
  stageSupplementIntakeSelection({ dailyPlanId: "7", intakeId: "3", selectionSession: "11", supplementId: 29 });

  assert.equal(consumeSupplementIntakeSelection("7", "other"), undefined);
  assert.deepEqual(consumeSupplementIntakeSelection("7", "3"), {
    dailyPlanId: "7",
    intakeId: "3",
    selectionSession: "11",
    supplementId: 29,
  });
  assert.equal(consumeSupplementIntakeSelection("7", "3"), undefined);
});

test("preset supplement selection is handed back once to the matching reusable intake", () => {
  stagePresetSupplementSelection({ presetId: "new", selectionSession: "4", supplementId: 18 });
  assert.equal(consumePresetSupplementSelection("other"), undefined);
  assert.deepEqual(consumePresetSupplementSelection("new"), { presetId: "new", selectionSession: "4", supplementId: 18 });
  assert.equal(consumePresetSupplementSelection("new"), undefined);
});

test("supplement intake navigation pops the selector and returns to its recorded origin", async () => {
  const panel = await readTestFile(path.resolve(process.cwd(), "src/components/supplements/supplement-intake-panel.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/app/libraries/daily-plans/[id]/supplement-intakes/[intakeId].tsx"), "utf8");
  const selector = await readTestFile(path.resolve(process.cwd(), "src/app/libraries/daily-plans/[id]/supplement-intakes/select.tsx"), "utf8");

  assertSourceMatch(panel, /usePathname\(\)[\s\S]*returnTo: pathname/);
  assertSourceMatch(detail, /internalHref\(returnTo\)[\s\S]*forceFallback: true/);
  assertSourceMatch(selector, /router\.canGoBack\(\)\) router\.back\(\)/);
  assertSourceMatch(selector, /stageSupplementIntakeSelection[\s\S]*close\(\)/);
  assertSourceDoesNotMatch(selector, /router\.dismissTo\(returnHref\)/);
});
