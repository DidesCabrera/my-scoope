import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("mobile libraries expose native creation for all four entities", async () => {
  const list = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const create = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-create-screen.tsx"), "utf8");
  const route = await readFile(path.resolve(process.cwd(), "src/app/libraries/create.tsx"), "utf8");

  for (const label of ["+ Crear alimento", "+ Crear comida", "+ Crear plan diario", "+ Crear programa"]) {
    assert.match(list, new RegExp(label.replace("+", "\\+")));
  }
  assert.match(list, /pathname: "\/libraries\/create"/);
  assert.match(list, /include_drafts/);
  assert.match(route, /LibraryCreateScreen/);
  assert.match(create, /mode: "back"/);
  assert.match(create, /action: \{ label: "Cancelar"/);
  assert.match(create, /<Card accent=\{tokens\.color\[entity\]\}/);
  assert.match(create, /<EntityIcon entity=\{entity\} size="compact" \/>/);
  for (const identity of ["Nuevo alimento", "Nueva comida", "Nuevo plan diario", "Nuevo programa"]) {
    assert.match(create, new RegExp(identity));
  }
  assert.match(create, /router\.replace\(`\/libraries\/\$\{config\.segment\}\/\$\{created\.id\}`/);
  assert.doesNotMatch(create, /AppHeader|CollectionPageHeader/);
  for (const field of ["Nombre", "Proteínas (g)", "Carbohidratos (g)", "Grasas (g)"]) {
    assert.match(create, new RegExp(field.replace(/[()]/g, "\\$&")));
  }
  for (const endpoint of ["foods", "meals", "daily-plans", "programs"]) {
    assert.match(create, new RegExp(`/api/v1/library/${endpoint}`));
  }
});

test("draft program cannot be calendarized before receiving a daily plan", async () => {
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  assert.match(detail, /item\.can_calendarize && !item\.is_draft/);
  assert.match(detail, /onAssignDailyPlan=\{item\.can_calendarize/);
});

test("empty drafts hide nutrition comparisons until they have comparable content", async () => {
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const detailPage = await readFile(path.resolve(process.cwd(), "src/components/details/entity-detail-page.tsx"), "utf8");
  const program = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8");

  assert.match(detail, /const isEmptyDraft = item\.is_draft && panelCount === 0/);
  assert.match(detail, /indicators=\{isEmptyDraft \? undefined : item\.indicators\}/);
  assert.match(detail, /showNutrition=\{!isEmptyDraft\}/);
  assert.match(detailPage, /showNutrition \? <NutritionKpiSection/);
  assert.match(program, /const hasPlans = filledDaysCount > 0/);
  assert.match(program, /const showProgramComparison = !item \|\| weeksCount > 1/);
  assert.match(program, /const showProgramStructure = !item \|\| plansCount > 0 \|\| weeksCount > 1/);
  assert.match(program, /\{hasPlans \? <StructuralIndicators/);
  assert.match(program, /\{showProgramComparison \? <>/);
  assert.match(program, /label="\+ Agregar nueva semana"/);
  assert.match(program, /label: "Duplicar semana"/);
  assert.match(program, /label: "Eliminar semana"/);
  assert.match(program, /canRemoveWeek=\{weeksCount > 1\}/);
  assert.ok(program.indexOf("<ProgramWeekComparisonPanels") < program.indexOf('label="+ Agregar nueva semana"'));
});
