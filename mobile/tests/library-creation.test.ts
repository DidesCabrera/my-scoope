import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("mobile libraries expose native creation for all four entities", async () => {
  const list = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const create = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-create-screen.tsx"), "utf8");
  const route = await readFile(path.resolve(process.cwd(), "src/app/libraries/create.tsx"), "utf8");

  for (const label of ["Crear alimento", "Crear comida", "Crear plan diario", "Crear programa"]) {
    assert.match(list, new RegExp(label));
  }
  assert.match(list, /pathname: "\/libraries\/create"/);
  assert.match(list, /createAction: mode === "list" \? \{ label: createLabels\[entity\]/);
  assert.doesNotMatch(list, /<Button label=\{createLabels\[entity\]\}/);
  assert.match(list, /include_drafts/);
  assert.match(route, /LibraryCreateScreen/);
  assert.match(create, /mode: "back"/);
  assert.match(create, /action: \{ label: "Cancelar"/);
  assert.match(create, /<Card accent=\{tokens\.color\[entity\]\}/);
  assert.match(create, /<EntityIcon entity=\{entity\} size="compact" \/>/);
  for (const identity of ["Nuevo alimento", "Nueva comida", "Nuevo plan diario", "Nuevo programa"]) {
    assert.match(create, new RegExp(identity));
  }
  assert.match(create, /const mealCreationContext = entity === "meal" && returnHref && pickerEntryHref && pickerKind/);
  assert.match(create, /pathname: "\/libraries\/meals\/\[id\]"/);
  assert.match(create, /pickerEntryTo: String\(mealCreationContext\.pickerEntryHref\)/);
  assert.match(create, /returnTo: String\(mealCreationContext\.returnHref\)/);
  assert.doesNotMatch(create, /AppHeader|CollectionPageHeader/);
  for (const field of ["Nombre", "Proteínas", "Carbohidratos", "Grasas totales"]) {
    assert.match(create, new RegExp(field.replace(/[()]/g, "\\$&")));
  }
  assert.match(create, /Valores por 100 \{portionUnit\}/);
  assert.match(create, /labelStyle=\{entity === "food" \? styles\.foodFieldLabel : undefined\}/);
  assert.match(create, /foodFieldLabel: \{ color: tokens\.color\.textMain \}/);
  assert.match(create, /nutritionLabel: \{ color: tokens\.color\.textMain[\s\S]*fontWeight: tokens\.weight\.bold/);
  assert.match(create, /style=\{styles\.nutritionInputSurface\}/);
  assert.match(create, /<Text style=\{styles\.nutritionUnit\}>g<\/Text>/);
  assert.match(create, /<DistributedTabBar<"g" \| "ml">[\s\S]*bleed/);
  for (const endpoint of ["foods", "meals", "daily-plans", "programs"]) {
    assert.match(create, new RegExp(`/api/v1/library/${endpoint}`));
  }
});

test("private foods can be edited through the prefilled food form", async () => {
  const create = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-create-screen.tsx"), "utf8");

  assert.match(create, /const editingFoodId = entity === "food"/);
  assert.match(create, /`\/api\/v1\/library\/foods\/\$\{editingFoodId\}`/);
  assert.match(create, /setName\(food\.name\)/);
  assert.match(create, /setProtein\(String\(food\.nutrition\.protein\.grams\)\)/);
  assert.match(create, /setCarbs\(String\(food\.nutrition\.carbs\.grams\)\)/);
  assert.match(create, /setFat\(String\(food\.nutrition\.fat\.grams\)\)/);
  assert.match(create, /method: editingFoodId \? "PUT" : "POST"/);
  assert.match(create, /editingFoodId \? "Editar alimento"/);
  assert.match(create, /editingFoodId \? "Guardar cambios"/);
});

test("meal creation returns to selection on cancel and advances with the created meal on done", async () => {
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");

  assert.match(detail, /const isContextualMealCreation = entitySlug === "meals"[\s\S]*Boolean\(pickerEntryHref\)/);
  assert.match(detail, /leadingAction: \{ label: "Cancelar", onPress: cancelContextualCreation \}/);
  assert.match(detail, /action: \{ disabled: item\?\.is_draft !== false, label: "Listo", onPress: continueContextualCreation \}/);
  assert.match(detail, /router\.dismissTo\(pickerEntryHref\)/);
  assert.match(detail, /router\.replace\(pickerConfigureHref\(contextualPickerKind/);
  assert.match(detail, /selectedId: createdMealId/);
  assert.match(detail, /returnTo: returnHref/);
  assert.match(detail, /returnTo: String\(currentDetailHref\)/);
  assert.match(navigation, /headerPresentation\.mode === "back" && headerPresentation\.leadingAction/);
  assert.match(navigation, /onPress=\{headerPresentation\.leadingAction\.onPress\}/);
  assert.match(navigation, /disabled=\{headerPresentation\.action\.disabled\}/);
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
  assert.match(detail, /const detailIndicators = isEmptyDraft \? undefined/);
  assert.match(detail, /showNutrition=\{!isEmptyDraft\}/);
  assert.match(detailPage, /showNutrition && nutrition \? <View style=\{styles\.kpiSection\}><NutritionKpiSection/);
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
