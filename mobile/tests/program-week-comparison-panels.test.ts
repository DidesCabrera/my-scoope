import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("week comparison uses full identities and per-plan macro averages", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-week-comparison-panels.tsx"),
    "utf8",
  );

  assert.ok(source.includes('<EntityIcon entity="program" size="compact" />'));
  assert.ok(source.includes("<Text style={styles.weekName}>Semana {week}</Text>"));
  assert.ok(!source.includes('key: "plans", label: "Planes"'));
  assert.ok(source.includes("function averagePerPlan(value: number, plans: number): number | null"));
  assert.ok(source.includes('label: "Pg"'));
  assert.ok(source.includes('label: "Cg"'));
  assert.ok(source.includes('label: "Fg"'));
  assert.ok(source.includes('mixedCaseHeaderText: { textTransform: "none" }'));
  assert.ok(source.includes("integer(week.proteinGrams / week.dailyPlans)"));
  assert.ok(source.includes("integer(week.carbsGrams / week.dailyPlans)"));
  assert.ok(source.includes("integer(week.fatGrams / week.dailyPlans)"));
});

test("calorie comparison labels and highlights its variation", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-week-comparison-panels.tsx"),
    "utf8",
  );

  assert.ok(source.includes('key: "average", label: "CAL prom", textStyle: styles.mixedCaseHeaderText'));
  assert.ok(source.includes('key: "delta", label: "% var", textStyle: styles.mixedCaseHeaderText'));
  assert.ok(source.includes("<Text style={[styles.cell, styles.dataCell]}>{integer(week.averageCalories)}</Text>"));
  assert.ok(source.includes("<CalorieVariationBadge value={delta} />"));
  assert.ok(source.includes('backgroundColor: tokens.color.kcalBorder, borderRadius: 5'));
  assert.ok(source.includes("minHeight: 22"));
  assert.ok(source.includes("calorieVariationBadgeText: { color: tokens.color.textMain"));
});
