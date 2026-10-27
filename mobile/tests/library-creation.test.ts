import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("mobile libraries expose native creation for all four entities", async () => {
  const list = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const create = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-create-screen.tsx"), "utf8");
  const route = await readFile(path.resolve(process.cwd(), "src/app/libraries/create.tsx"), "utf8");

  for (const label of ["Crear alimento", "Crear comida", "Crear minuta diaria", "Crear programa"]) {
    assert.match(list, new RegExp(label));
  }
  assert.match(list, /pathname: "\/libraries\/create"/);
  assert.match(list, /createAction: mode === "list" \? \{ label: createLabels\[entity\]/);
  assert.doesNotMatch(list, /<Button label=\{createLabels\[entity\]\}/);
  assert.match(list, /include_drafts/);
  assert.match(route, /LibraryCreateScreen/);
  assert.match(create, /mode: "back"/);
  assert.match(create, /fallback: `\/libraries\/\$\{config\.segment\}`/);
  assert.match(create, /<View style=\{styles\.formBody\}>/);
  for (const title of ["Crear nuevo alimento", "Crear nueva comida", "Crear nueva minuta diaria", "Crear nuevo programa"]) {
    assert.match(create, new RegExp(title));
  }
  assert.ok(create.indexOf("<View style={styles.formBody}>") < create.indexOf("{config.guidance ?"));
  assert.match(create, /const mealCreationContext = entity === "meal" && returnHref && pickerEntryHref && pickerKind/);
  assert.match(create, /const detailHref = `\/libraries\/meals\/\$\{saved\.id\}/);
  assert.match(create, /pickerEntryTo: String\(mealCreationContext\.pickerEntryHref\)/);
  assert.match(create, /returnTo: String\(mealCreationContext\.returnHref\)/);
  assert.doesNotMatch(create, /AppHeader/);
  for (const field of ["Nombre", "Proteínas", "Carbohidratos", "Grasas totales"]) {
    assert.match(create, new RegExp(field.replace(/[()]/g, "\\$&")));
  }
  assert.equal(create.includes("Valores por 100 {portionUnit}"), true);
  assert.equal(create.includes('labelStyle={entity === "food" ? styles.foodFieldLabel : undefined}'), true);
  assert.equal(create.includes("foodFieldLabel: { color: tokens.color.textMuted }"), true);
  assert.ok(create.includes("nutritionLabel: { color: tokens.color.textMain") && create.includes("fontWeight: tokens.weight.bold"));
  assert.equal(create.includes("style={styles.nutritionInputSurface}"), true);
  assert.equal(create.includes('<Text style={styles.nutritionUnit}>g</Text>'), true);
  assert.ok(create.includes('<DistributedTabBar<"g" | "ml">') && create.includes("bleed"));
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
});
