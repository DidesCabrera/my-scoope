import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

const source = (relativePath: string) => readTestFile(path.resolve(process.cwd(), relativePath), "utf8");

test("accumulated food lists expose the shared check column in active and library surfaces", async () => {
  const groupedFoods = await source("src/components/panels/grouped-foods-card.tsx");
  assertSourceMatch(groupedFoods, /useState<Set<string>>/);
  assertSourceMatch(groupedFoods, /const checklist = preparation \?\?/);
  assertSourceMatch(groupedFoods, /<FoodPanels items=\{items\} preparation=\{checklist\} preparationFirst=\{preparationFirst\} showPreparationColumn/);
  for (const relativePath of ["src/components/libraries/library-detail-screen.tsx", "src/components/libraries/program-detail-preview.tsx", "src/components/calendarization/calendarized-program-planning.tsx", "src/app/program/days/[id].tsx"]) {
    assertSourceMatch(await source(relativePath), /<GroupedFoodsCard/);
  }
});

test("shopping and cooking commitment lists use the shared check column", async () => {
  for (const relativePath of ["src/app/calendar/commitments.tsx", "src/app/calendar/commitments/[id].tsx"]) {
    const contents = await source(relativePath);
    assert.ok(contents.includes("<GroupedFoodsCard"));
    assert.ok(!contents.includes("showChecklist={false}"));
    assertSourceMatch(contents, /Alimentos para cocinar/);
  }
});

test("commitment detail presents its date like the day detail header", async () => {
  const detail = await source("src/app/calendar/commitments/[id].tsx");
  assertSourceMatch(detail, /subtitle=\{headerDate\(date\)\} subtitleStyle=\{styles\.dateSubtitle\}/);
  assertSourceMatch(detail, /title=\{commitmentActionLabel\[commitment\.kind\]\}/);
  assertSourceMatch(detail, /title: commitment \? commitmentActionLabel\[commitment\.kind\]/);
  assertSourceMatch(detail, /dateSubtitle: \{ fontSize: 17, fontWeight: "600", lineHeight: 23, marginTop: -4 \}/);
  assertSourceDoesNotMatch(detail, /indicator=\{<Chip[^>]*label=\{shortDate\(date\)\}/);
});

test("commitment detail delegates food-list generation to a dedicated screen", async () => {
  const detail = await source("src/app/calendar/commitments/[id].tsx");
  const generator = await source("src/app/calendar/commitments/[id]/foods.tsx");
  const groupedFoods = await source("src/components/panels/grouped-foods-card.tsx");
  assertSourceMatch(detail, /!periodSaved \? <View style=\{styles\.emptyFoodSection\}>[\s\S]*Aún no tiene una lista de alimentos asociada[\s\S]*label="Generar lista de alimentos" onPress=\{openFoodListGenerator\}/);
  assertSourceMatch(detail, /router\.push\(`\/calendar\/commitments\/\$\{commitment\.id\}\/foods\?date=\$\{commitment\.calendar_date\}`/);
  assertSourceMatch(detail, />Lista de alimentos asociada<\/Text>[\s\S]*chipsAction=\{<Button bleed=\{false\} label="Editar periodo" onPress=\{openFoodListGenerator\}/);
  assertSourceDoesNotMatch(detail, /calendarFoodDayRole|Calcular lista de alimentos|foodPeriodControls/);
  assertSourceDoesNotMatch(detail, /Lista guardada en este compromiso/);
  assertSourceMatch(detail, /notice === "Nota guardada\." \? <InlineNotice tone="info">\{notice\}<\/InlineNotice>/);
  assertSourceMatch(generator, /title="Generar lista de alimentos"/);
  assertSourceMatch(generator, /icon=\{<List color=\{tokens\.color\.textMain\} size=\{28\}/);
  assertSourceMatch(generator, /apiRequest<CalendarPeriodFoodsData>\(`\/api\/v1\/calendar\/foods\?start_date=\$\{start\}&end_date=\$\{end\}`\)/);
  assertSourceMatch(generator, /label="Generar lista de alimentos"[\s\S]*label="Limpiar selección"[\s\S]*onPress=\{clearPeriod\}/);
  assertSourceMatch(generator, /<View style=\{styles\.confirmActions\}>[\s\S]*label="Asociar lista de alimentos"[\s\S]*associateList[\s\S]*label="Editar periodo"[\s\S]*<GroupedFoodsCard/);
  assertSourceMatch(generator, /update_food_period: true, food_period_start: start, food_period_end: end/);
  assertSourceMatch(generator, /Alert\.alert\("Lista asociada con éxito"[\s\S]*router\.back\(\)/);
  assertSourceMatch(groupedFoods, /\{chipsAction\}[\s\S]*<FoodPanels/);
});

test("shopping and cooking registration cards use a compact full-width muted list action", async () => {
  const registration = await source("src/app/calendar/commitments.tsx");
  const pickerAction = await source("src/components/pickers/picker-card-action.tsx");
  assertSourceDoesNotMatch(registration, /Sin lista de alimentos adjunta/);
  assertSourceMatch(registration, /variant="mutedFullWidth"/);
  assertSourceMatch(registration, /icon=\{<List[\s\S]*Crear lista de alimentos/);
  assertSourceMatch(registration, /label="Crear lista de alimentos"[\s\S]*onPress=\{\(\) => openFoodGenerator\(date\)\}/);
  assertSourceMatch(registration, /onPress=\{\(\) => openFoodDetail\(date\)\}/);
  assertSourceMatch(registration, />Días seleccionados · \{selected\.length\}<\/Text>/);
  assertSourceMatch(registration, />Días comprometidos previamente · \{existingCommitments\.length\}<\/Text>/);
  assertSourceMatch(registration, /día comprometido.*días comprometidos/);
  assertSourceMatch(registration, /Agregar compras al calendario/);
  assertSourceMatch(registration, /Selecciona las fechas que desees/);
  assertSourceMatch(registration, /Días seleccionados · \{selected\.length\}[\s\S]*label=\{`Registrar \$\{selected\.length\} \$\{selected\.length === 1 \? "día" : "días"\} \$\{commitmentRegistrationSubject\[kind\]\}`\}[\s\S]*Días comprometidos previamente/);
  assertSourceMatch(registration, /shopping: "de compras"[\s\S]*cooking: "de cocinar"[\s\S]*training: "de entrenamiento"[\s\S]*nutritionist: "con nutricionista"/);
  assertSourceMatch(registration, /calendar\/commitments\?kind=\$\{kind\}&from_date=\$\{today\}/);
  assertSourceMatch(registration, /loadExistingCommitments\(result\.local_date, result\.future_commitments_count_by_kind\?\.\[kind\]/);
  assertSourceMatch(registration, /apiRequest<\{ deleted_id: number \}>\(`\/api\/v1\/calendar\/commitments\/\$\{commitment\.id\}`[\s\S]*method: "DELETE"/);
  assertSourceMatch(pickerAction, /actionMutedFullWidth: \{ alignSelf: "stretch", backgroundColor: tokens\.color\.surfaceMuted, minHeight: 38, width: "100%" \}/);
  assertSourceMatch(pickerAction, /labelMutedFullWidth: \{ color: tokens\.color\.textMain \}/);
});

test("deleting a commitment returns with the backward transition", async () => {
  const detail = await source("src/app/calendar/commitments/[id].tsx");
  assertSourceMatch(detail, /async function deleteCommitment\(\)[\s\S]*router\.back\(\)/);
  assertSourceDoesNotMatch(detail, /async function deleteCommitment\(\)[\s\S]*router\.replace\("\/calendar\/registry"/);
  assertSourceDoesNotMatch(detail, /async function deleteCommitment\(\)[\s\S]*router\.dismissTo\("\/calendar\/registry"/);
});

test("commitment registration reuses the explicit generate, associate, and detail flow", async () => {
  const registration = await source("src/app/calendar/commitments.tsx");
  for (const value of ['title="Generar lista de alimentos"', 'label="Generar lista de alimentos"', 'label="Limpiar selección"', 'label="Asociar lista de alimentos"', 'label="Editar periodo"', 'showContents={Boolean(foodPreview)}', 'setFoodAttachments((current) => ({ ...current, [day]: { start: foodStartDate, end: foodEndDate } }))', 'food_attachments: selected.flatMap', 'key={`commitment-detail-${editingFoodDate}`}', 'key={`commitment-generator-${editingFoodDate}`}', 'indicator={<Chip']) {
    assert.ok(registration.includes(value), value);
  }
  assertSourceMatch(registration, /icon=\{<List color=\{tokens\.color\.textMain\} size=\{28\}/);
  assertSourceMatch(registration, /Alert\.alert\("Lista asociada con éxito"[\s\S]*onPress: closeFoodEditor/);
  assertSourceMatch(registration, />Lista de alimentos asociada<\/Text>[\s\S]*chipsAction=\{<Button bleed=\{false\} label="Editar periodo"/);
});
