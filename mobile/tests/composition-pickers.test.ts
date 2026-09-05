import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

function matches(source: string, pattern: RegExp) {
  assert.match(source, pattern);
}

function omits(source: string, pattern: RegExp) {
  assert.doesNotMatch(source, pattern);
}

test("composition pickers use independent native routes and one shared flow", async () => {
  const picker = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/composition-picker-screen.tsx"),
    "utf8",
  );
  matches(picker, /mode: "back"/);
  matches(picker, /stickyHeaderIndices=\{\[0\]\}/);
  matches(picker, /stickyHeaderIndices=\{\[1\]\}/);
  matches(picker, /style=\{styles\.configurationSticky\}/);
  matches(picker, /style=\{styles\.selectionSticky\}/);
  matches(picker, /style=\{styles\.searchField\}/);
  matches(picker, /if \(!selectedId\) \{/);
  matches(picker, /<PickerEntryTabs/);
  for (const createLabel of ["Crear alimento", "Crear comida", "Crear plan diario"]) {
    matches(picker, new RegExp(createLabel));
  }
  matches(picker, /pathname: "\/libraries\/create"/);
  matches(picker, /params: \{ entity: config\.createEntity \}/);
  assert.ok(picker.indexOf("<PickerEntryTabs") < picker.indexOf("<View style={styles.searchField}"));
  matches(picker, /NutritionEntityCard/);
  matches(picker, /import \{ PickerCardAction \} from "\.\/picker-card-action"/);
  matches(picker, /<PickerCardAction label=\{actionLabel\} onPress=\{onAction\} subject=\{option\.name\} \/>/);
  matches(picker, /actionLabel="Seleccionar"/);
  matches(picker, /router\.push\(pickerConfigureHref/);
  matches(picker, /onPress: \(\) => router\.dismissTo\(detailHref\)/);
  matches(picker, /<PickerOptionCard\s+option=\{selected\}/);
  omits(picker, /Cambiar selección/);
  omits(picker, /<Button label="Cambiar selección"/);
  omits(picker, /<Button label="Cancelar"/);
  omits(picker, /config\.eyebrow|styles\.heading|Destino:/);
  omits(picker, /Configura la selección/);
  matches(picker, /Previsualización del impacto/);
  matches(picker, /preview\?\.result/);
  matches(picker, /<PickerResultCard preview=\{preview\} \/>/);
  const selectedCard = picker.indexOf("option={selected}");
  const configuration = picker.indexOf("style={styles.configurationSticky}");
  const impactPreview = picker.indexOf('title="Previsualización del impacto"');
  assert.ok(selectedCard < configuration);
  assert.ok(configuration < impactPreview);
  matches(picker, /Porción \(g\)/);
  matches(picker, /<Scale color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  matches(picker, /<Clock color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  matches(picker, /<NotebookPen color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  matches(picker, /<CalendarDays color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  matches(picker, /<Text style=\{styles\.compactFieldLabel\}>Porción \(g\)<\/Text>/);
  matches(picker, /style=\{styles\.compactFieldInput\} value=\{quantity\}/);
  omits(picker, /setQuantity\(value\); setPreview\(null\)/);
  matches(picker, /setPreviewPayloadKey\(payloadKey\)/);
  matches(picker, /disabled=\{!configurationValid \|\| previewing \|\| previewPayloadKey !== payloadKey\}/);
  matches(picker, /style=\{styles\.previewHeading\}/);
  matches(picker, /previewHeading: \{[^}]*justifyContent: "space-between"[^}]*width: "100%"/);
  omits(picker, /Actualizando previsualización/);
  matches(picker, /Hora \(HH:MM\)/);
  matches(picker, /style=\{styles\.configurationDivider\}/);
  matches(picker, /accessibilityLabel=\{noteEditing \? "Ocultar edición de nota" : "Editar nota"\}/);
  matches(picker, /noteEditing \? <TextInput/);
  matches(picker, /configurationSticky: \{[^}]*marginHorizontal: -tokens\.spacing\.screen[^}]*paddingHorizontal: tokens\.spacing\.screen/);
  matches(picker, /height: 34[^}]*width: 34/);
  omits(picker, /function toggleDay\(day: number\) \{[^}]*setPreview\(null\)/s);
  matches(picker, /day_numbers/);
  matches(picker, /confirm_replacements/);
  matches(picker, /Confirmar reemplazos/);
  matches(picker, /PickerPreview/);
  matches(picker, /dailyplan_meal_id: relationId/);
  matches(picker, /meal_food_id: relationId/);
  matches(picker, /Reemplazar alimento/);
  matches(picker, /target\.panel\.foods\.find\(\(item\) => item\.relation_id === relationId\)/);
  matches(picker, /setQuantity\(String\(relation\.quantity\)\)/);
  matches(picker, /const detailHref = returnTo \?\?/);
  matches(picker, /pickerConfigureHref\(kind, \{ contextDailyPlanId, contextDailyPlanMealId, dayNumber: initialDayNumber, relationId, returnTo/);
  matches(picker, /dailyplan_id: contextDailyPlanId/);
  matches(picker, /dailyplan_meal_id: contextDailyPlanMealId/);
  omits(picker, /protein\s*\*\s*4|carbs\s*\*\s*4|fat\s*\*\s*9/);

  const cardAction = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-card-action.tsx"),
    "utf8",
  );
  matches(cardAction, /accessibilityLabel=\{`\$\{label\}: \$\{subject\}`\}/);
  matches(cardAction, /backgroundColor: tokens\.color\.textMain/);
  matches(cardAction, /borderRadius: tokens\.radius\.pill/);
  matches(cardAction, /minHeight: 38/);

  const entryTabs = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-entry-tabs.tsx"),
    "utf8",
  );
  matches(entryTabs, /styles\.entryTabsBar/);
  matches(entryTabs, /styles\.entryTabActive/);
  matches(entryTabs, /icon: Bookmark/);
  matches(entryTabs, /icon: Plus/);
  matches(entryTabs, /entryTab: \{[^}]*flex: 1/);
  matches(entryTabs, /borderRadius: tokens\.radius\.pill/);
  matches(entryTabs, /backgroundColor: tokens\.color\.textMain/);
  matches(entryTabs, /Mi librería/);

  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  matches(navigation, /mode: "back"/);
  matches(navigation, /ChevronLeft/);
  matches(navigation, /BackHeaderIdentity/);
  matches(navigation, /backHeaderAction/);
  matches(picker, /action: \{ label: "Cancelar"/);

  for (const route of ["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program"]) {
    const source = await readFile(path.resolve(process.cwd(), `src/app/pickers/${route}.tsx`), "utf8");
    matches(source, /CompositionPickerScreen/);
  }
  const configureRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/configure.tsx"), "utf8");
  matches(configureRoute, /selectedId/);
  matches(configureRoute, /CompositionPickerScreen/);
  matches(configureRoute, /selectedId=\{selection\}/);
  matches(configureRoute, /returnTo=\{returnHref\}/);
  matches(configureRoute, /contextDailyPlanId=\{Number\(contextDailyPlanId\) \|\| undefined\}/);
  matches(configureRoute, /animation: "slide_from_right"/);

  const resultCard = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-result-card.tsx"),
    "utf8",
  );
  matches(resultCard, /Comida resultante/);
  matches(resultCard, /Plan diario resultante/);
  matches(resultCard, /preview\.selection\.entity === "food"/);
  matches(resultCard, /projectedMeal\.foods\.map\(foodPanelItem\)/);
  matches(resultCard, /ProgramDayComparisonPanels/);
  matches(resultCard, /result\.entity === "week" && week/);
  matches(resultCard, /<EntityCard entity="program" eyebrow="Resultado proyectado" title=\{result\.name\}>/);
  matches(resultCard, /<EntityCardPanelSlot>/);
  matches(resultCard, /result\.panel\.foods\.map\(foodPanelItem\)/);
  matches(resultCard, /result\.panel\.meals\.map\(mealPanelItem\)/);
  matches(resultCard, /projectedLabel: item\.projected_label/);

  const foodRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/food-to-meal.tsx"), "utf8");
  matches(foodRoute, /mealFoodId/);
  matches(foodRoute, /relationId=\{relationId\}/);

  const weekRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/week-to-program.tsx"), "utf8");
  matches(weekRoute, /week-picker\/preview/);
  matches(weekRoute, /Nueva semana/);
  matches(weekRoute, /Creando nueva semana/);
  matches(weekRoute, /expected_week_number=\$\{nextPreview\.selection\.id\}/);
  matches(weekRoute, /router\.replace\(`\/pickers\/week-to-program\?programId=\$\{targetId\}&weekNumber=\$\{result\.created_id\}`/);
  matches(weekRoute, /<ProgramWeekDetail/);
  matches(weekRoute, /pickerHref\("dailyplan-to-program"/);
  matches(weekRoute, /returnTo: String\(returnHref\)/);
  matches(weekRoute, /label: hasCreatedWeek \? "Finalizar" : "Cancelar"/);
});

test("library details open every composition flow and program days remain editable", async () => {
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  for (const route of ["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program", "week-to-program"]) {
    matches(detail, new RegExp(route));
  }
  matches(detail, /label="\+ Agregar alimento"/);
  matches(detail, /label="\+ Agregar Comida"/);
  const comparisonSection = detail.indexOf('title={sectionTitles[item.panel.kind]}');
  assert.ok(comparisonSection < detail.indexOf('label="+ Agregar alimento"'));
  assert.ok(comparisonSection < detail.indexOf('label="+ Agregar Comida"'));
  assert.ok(detail.indexOf('label="+ Agregar Comida"') < detail.indexOf('title="Detalle de cada Comida"'));
  matches(detail, /FoodPanels editing=\{foodEditing\}/);
  matches(detail, /MealPanels editing=\{mealEditing\}/);
  matches(detail, /foods\/order/);
  matches(detail, /meals\/order/);
  matches(detail, /pickerHref\("food-to-meal", \{ mealFoodId: food\.relationId, mealId: item\.id, \.\.\.\(hasMealTimeContext/);
  matches(detail, /dailyPlanMealId: contextDailyPlanMealId/);

  const panels = await readFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  matches(panels, /FoodEditPanel/);
  matches(panels, /MealEditPanel/);
  matches(panels, /label: "Editar"/);
  matches(panels, /Guardar orden/);
  matches(panels, /label=\{`Reemplazar \$\{item\.name\}`\}/);
  matches(panels, /editing\.onReplace\(item\)/);

  const program = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8");
  const assignedPlan = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"), "utf8");
  matches(program, /onAssignDailyPlan/);
  matches(assignedPlan, /Reemplazar plan diario/);
  matches(assignedPlan, /Quitar plan diario/);
  matches(program, /allowEmptySelection/);
});
