import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("program week detail presents planning before food and comparison insights", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  const typography = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/typography.tsx"),
    "utf8",
  );
  const weekDetail = source.slice(
    source.indexOf("export function ProgramWeekDetail"),
    source.indexOf("type ProgramDetailPreviewProps"),
  );

  const dailyPlans = weekDetail.indexOf('title="Planes diarios esta semana"');
  const daysGrid = weekDetail.indexOf("<ProgramDaysGrid");
  const foods = weekDetail.indexOf('title="Alimentos en esta semana"');
  const foodPanels = weekDetail.indexOf("<GroupedFoodsCard");
  const dividerAfterFoods = weekDetail.indexOf('<SectionDivider spacing="compact" tone="soft" />', foodPanels);
  const weeklyChartTitle = weekDetail.indexOf('title="Gráfico de la semana"');
  const weeklyChart = weekDetail.indexOf("<ProgramMetricPreview");
  const comparison = weekDetail.indexOf('title="Tabla de comparación entre planes diarios"');

  assert.ok(dailyPlans >= 0);
  assert.ok(dailyPlans < daysGrid);
  assert.ok(daysGrid < foods);
  assert.ok(foods < weeklyChart);
  assert.ok(weeklyChart < comparison);
  assert.ok(foods < foodPanels);
  assert.match(weekDetail, /<GroupedFoodsCard title=\{`Alimentos semana \$\{week\}`\}/);
  assert.ok(foodPanels < dividerAfterFoods);
  assert.ok(dividerAfterFoods < weeklyChartTitle);
  assert.ok(weeklyChartTitle < weeklyChart);
  assert.match(typography, /normalizedTitle === "gráfico de la semana"/);
  assert.match(typography, /titleIcon === "chart" \? <Activity/);
  assert.match(weekDetail, /<View style=\{styles\.weekChartSection\}>[\s\S]*title="Gráfico de la semana"[\s\S]*<ProgramMetricPreview/);
  assert.match(source, /weekChartSection: \{ gap: tokens\.spacing\.md/);
  assert.ok(!weekDetail.includes('<SectionDivider spacing="compact" tone="soft" />\n        <SectionHeading detail={`${filledDaysCount} asignados`} title="Planes diarios esta semana"'));
});

test("grouped foods card owns the food identity and existing comparison panel", async () => {
  const card = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/grouped-foods-card.tsx"),
    "utf8",
  );

  assert.match(card, /<Card accent=\{tokens\.color\.food\}>/);
  assert.match(card, /<EntityHeading entity="food" eyebrow="Alimentos agrupados" title=\{title\} \/>/);
  assert.match(card, /<FoodPanels \{\.\.\.panelProps\} \/>/);
});

test("embedded program detail does not clip lateral content with a nested scroll viewport", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  const embeddedBranch = source.slice(source.indexOf("if (scrollable)"), source.indexOf("const styles"));

  assert.match(embeddedBranch, /return \([\s\S]*<View style=\{styles\.page\}>/);
  assert.doesNotMatch(embeddedBranch, /scrollEnabled=\{false\}/);
});

test("proposed program owns its scroll so week tabs stay below the header", async () => {
  const route = await readTestFile(
    path.resolve(process.cwd(), "src/app/proposals/[id]/program.tsx"),
    "utf8",
  );
  const preview = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );

  assert.match(route, /<Screen contentStyle=\{styles\.screen\} headerMode="preserve" scroll=\{false\}>/);
  assert.match(route, /<ProposalProgramPreview[\s\S]*scrollable/);
  assert.match(preview, /stickyHeaderIndices=\{\[3\]\}/);
});
