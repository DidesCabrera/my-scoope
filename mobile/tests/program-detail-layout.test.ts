import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("program week detail presents weekly charts before the day selector and foods", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  const weekDetail = source.slice(
    source.indexOf("export function ProgramWeekDetail"),
    source.indexOf("type ProgramDetailPreviewProps"),
  );

  const daysGrid = weekDetail.indexOf("<ProgramDaysGrid");
  const foods = weekDetail.indexOf("Alimentos en Semana");
  const foodPanels = weekDetail.indexOf("<GroupedFoodsCard");
  const weeklyChart = weekDetail.indexOf("<WeekMetricPreview");
  const dailyPlansHeading = weekDetail.indexOf("Planes diarios en Semana");

  assert.doesNotMatch(weekDetail, /Planes diarios esta semana|\$\{filledDaysCount\} asignados/);
  assert.ok(daysGrid >= 0);
  assert.ok(weeklyChart < daysGrid);
  assert.ok(weeklyChart < dailyPlansHeading);
  assert.ok(dailyPlansHeading < daysGrid);
  assert.ok(daysGrid < foods);
  assert.ok(foods < foodPanels);
  assert.match(weekDetail, /<GroupedFoodsCard title=\{`Alimentos semana \$\{week\}`\}/);
  assert.ok(source.indexOf('{ key: "calories", label: "Calorías" }') < source.indexOf('{ key: "all", label: "Todos" }'));
  assert.match(source, /weekChartSection: \{ gap: tokens\.spacing\.md/);
  assert.ok(!weekDetail.includes('<SectionDivider spacing="compact" tone="soft" />\n        <SectionHeading detail={`${filledDaysCount} asignados`} title="Planes diarios esta semana"'));
});

test("grouped foods card owns the food identity and existing comparison panel", async () => {
  const card = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/grouped-foods-card.tsx"),
    "utf8",
  );

  assert.match(card, /<Card accent=\{tokens\.color\.food\}>/);
  assert.match(card, /<EntityHeading entity="food" eyebrow="LISTA DE ALIMENTOS" title=\{title\} \/>/);
  assert.match(card, /<Chip backgroundColor=\{`\$\{tokens\.color\.food\}1A`\} borderColor=\{tokens\.color\.food\} label=\{countLabel\} textColor=\{tokens\.color\.textMain\} \/>/);
  assert.match(card, /<FoodPanels items=\{items\} preparation=\{checklist\} preparationFirst=\{preparationFirst\} showPreparationColumn \{\.\.\.panelProps\} \/>/);
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
});

test("program planning uses the descriptive section header without an overview divider", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );

});

test("program and week charts expose separate UI system variants", async () => {
  const [detail, charts] = await Promise.all([
    readTestFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8"),
    readTestFile(path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"), "utf8"),
  ]);

});

test("program detail matches standard bottom spacing and separates the calendarization action", async () => {
  const [detail, route] = await Promise.all([
    readTestFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8"),
    readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8"),
  ]);

});
