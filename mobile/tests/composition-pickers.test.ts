import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("composition pickers use independent native routes and one shared flow", async () => {
  const picker = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/composition-picker-screen.tsx"),
    "utf8",
  );
  assert.match(picker, /mode: "back"/);
  assert.match(picker, /stickyHeaderIndices=\{\[0\]\}/);
  assert.match(picker, /style=\{styles\.selectionSticky\}/);
  assert.match(picker, /style=\{styles\.searchField\}/);
  assert.match(picker, /if \(!selectedId\) \{/);
  assert.match(picker, /<PickerEntryTabs/);
  assert.match(picker, /styles\.entryTabsBar/);
  assert.match(picker, /styles\.entryTabActive/);
  assert.match(picker, /icon: Bookmark/);
  assert.match(picker, /icon: Plus/);
  assert.match(picker, /entryTab: \{[^}]*flex: 1/);
  assert.match(picker, /borderRadius: tokens\.radius\.pill/);
  assert.match(picker, /backgroundColor: tokens\.color\.textMain/);
  assert.match(picker, /Mi librería/);
  for (const createLabel of ["Crear alimento", "Crear comida", "Crear plan diario"]) {
    assert.match(picker, new RegExp(createLabel));
  }
  assert.match(picker, /pathname: "\/libraries\/create"/);
  assert.match(picker, /params: \{ entity: config\.createEntity \}/);
  assert.ok(picker.indexOf("<PickerEntryTabs") < picker.indexOf("<View style={styles.searchField}"));
  assert.match(picker, /NutritionEntityCard/);
  assert.match(picker, /styles\.selectButton/);
  assert.match(picker, /actionLabel="Seleccionar"/);
  assert.match(picker, /router\.push\(pickerConfigureHref/);
  assert.match(picker, /onPress: \(\) => router\.dismissTo\(detailHref\)/);
  assert.match(picker, /onAction=\{\(\) => router\.back\(\)\}/);
  assert.match(picker, /actionLabel="Cambiar selección"/);
  assert.doesNotMatch(picker, /<Button label="Cambiar selección"/);
  assert.doesNotMatch(picker, /<Button label="Cancelar"/);
  assert.doesNotMatch(picker, /config\.eyebrow|styles\.heading|Destino:/);
  assert.match(picker, /Configura la selección/);
  assert.match(picker, /Previsualización del impacto/);
  assert.match(picker, /preview && kind !== "dailyplan-to-program"/);
  const selectedCard = picker.indexOf('actionLabel="Cambiar selección"');
  const configuration = picker.indexOf('title="Configura la selección"');
  const impactPreview = picker.indexOf('title="Previsualización del impacto"');
  assert.ok(selectedCard < configuration);
  assert.ok(configuration < impactPreview);
  assert.match(picker, /Porción \(g\)/);
  assert.match(picker, /Hora \(HH:MM\)/);
  assert.match(picker, /day_numbers/);
  assert.match(picker, /confirm_replacements/);
  assert.match(picker, /Confirmar reemplazos/);
  assert.match(picker, /PickerPreview/);
  assert.match(picker, /dailyplan_meal_id: relationId/);
  assert.match(picker, /const detailHref = returnTo \?\?/);
  assert.match(picker, /pickerConfigureHref\(kind, \{ dayNumber: initialDayNumber, relationId, returnTo/);
  assert.doesNotMatch(picker, /protein\s*\*\s*4|carbs\s*\*\s*4|fat\s*\*\s*9/);

  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  assert.match(navigation, /mode: "back"/);
  assert.match(navigation, /ChevronLeft/);
  assert.match(navigation, /BackHeaderIdentity/);
  assert.match(navigation, /backHeaderAction/);
  assert.match(picker, /action: \{ label: "Cancelar"/);

  for (const route of ["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program"]) {
    const source = await readFile(path.resolve(process.cwd(), `src/app/pickers/${route}.tsx`), "utf8");
    assert.match(source, /CompositionPickerScreen/);
  }
  const configureRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/configure.tsx"), "utf8");
  assert.match(configureRoute, /selectedId/);
  assert.match(configureRoute, /CompositionPickerScreen/);
  assert.match(configureRoute, /selectedId=\{selection\}/);
  assert.match(configureRoute, /returnTo=\{returnHref\}/);
  assert.match(configureRoute, /animation: "slide_from_right"/);

  const weekRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/week-to-program.tsx"), "utf8");
  assert.match(weekRoute, /week-picker\/preview/);
  assert.match(weekRoute, /Nueva semana/);
  assert.match(weekRoute, /Creando nueva semana/);
  assert.match(weekRoute, /expected_week_number=\$\{nextPreview\.selection\.id\}/);
  assert.match(weekRoute, /router\.replace\(`\/pickers\/week-to-program\?programId=\$\{targetId\}&weekNumber=\$\{result\.created_id\}`/);
  assert.match(weekRoute, /<ProgramWeekDetail/);
  assert.match(weekRoute, /pickerHref\("dailyplan-to-program"/);
  assert.match(weekRoute, /returnTo: String\(returnHref\)/);
  assert.match(weekRoute, /label: hasCreatedWeek \? "Finalizar" : "Cancelar"/);
});

test("library details open every composition flow and program days remain editable", async () => {
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  for (const route of ["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program", "week-to-program"]) {
    assert.match(detail, new RegExp(route));
  }
  assert.match(detail, /label="\+ Agregar alimento"/);
  assert.match(detail, /label="\+ Agregar Comida"/);
  const comparisonSection = detail.indexOf('title={sectionTitles[item.panel.kind]}');
  assert.ok(comparisonSection < detail.indexOf('label="+ Agregar alimento"'));
  assert.ok(comparisonSection < detail.indexOf('label="+ Agregar Comida"'));
  assert.ok(detail.indexOf('label="+ Agregar Comida"') < detail.indexOf('title="Detalle de cada Comida"'));
  assert.match(detail, /FoodPanels editing=\{foodEditing\}/);
  assert.match(detail, /MealPanels editing=\{mealEditing\}/);
  assert.match(detail, /foods\/order/);
  assert.match(detail, /meals\/order/);

  const panels = await readFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  assert.match(panels, /FoodEditPanel/);
  assert.match(panels, /MealEditPanel/);
  assert.match(panels, /label: "Editar"/);
  assert.match(panels, /Guardar orden/);

  const program = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8");
  const assignedPlan = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"), "utf8");
  assert.match(program, /onAssignDailyPlan/);
  assert.match(assignedPlan, /Reemplazar plan diario/);
  assert.match(assignedPlan, /Quitar plan diario/);
  assert.match(program, /allowEmptySelection/);
});
