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
  assert.match(picker, /stickyHeaderIndices=\{\[1\]\}/);
  assert.match(picker, /style=\{styles\.configurationSticky\}/);
  assert.match(picker, /style=\{styles\.selectionSticky\}/);
  assert.match(picker, /style=\{styles\.searchField\}/);
  assert.match(picker, /if \(!selectedId\) \{/);
  assert.match(picker, /<PickerEntryTabs/);
  for (const createLabel of ["Crear alimento", "Crear comida", "Crear plan diario"]) {
    assert.match(picker, new RegExp(createLabel));
  }
  assert.match(picker, /pathname: "\/libraries\/create"/);
  assert.match(picker, /params: \{ entity: config\.createEntity \}/);
  assert.ok(picker.indexOf("<PickerEntryTabs") < picker.indexOf("<View style={styles.searchField}"));
  assert.match(picker, /NutritionEntityCard/);
  assert.match(picker, /import \{ PickerCardAction \} from "\.\/picker-card-action"/);
  assert.match(picker, /<PickerCardAction label=\{actionLabel\} onPress=\{onAction\} subject=\{option\.name\} \/>/);
  assert.match(picker, /actionLabel="Seleccionar"/);
  assert.match(picker, /router\.push\(pickerConfigureHref/);
  assert.match(picker, /onPress: \(\) => router\.dismissTo\(detailHref\)/);
  assert.match(picker, /<PickerOptionCard\s+option=\{selected\}/);
  assert.doesNotMatch(picker, /Cambiar selección/);
  assert.doesNotMatch(picker, /<Button label="Cambiar selección"/);
  assert.doesNotMatch(picker, /<Button label="Cancelar"/);
  assert.doesNotMatch(picker, /config\.eyebrow|styles\.heading|Destino:/);
  assert.doesNotMatch(picker, /Configura la selección/);
  assert.match(picker, /Previsualización del impacto/);
  assert.match(picker, /preview\?\.result/);
  assert.match(picker, /<PickerResultCard preview=\{preview\} \/>/);
  const selectedCard = picker.indexOf("option={selected}");
  const configuration = picker.indexOf("style={styles.configurationSticky}");
  const impactPreview = picker.indexOf('title="Previsualización del impacto"');
  assert.ok(selectedCard < configuration);
  assert.ok(configuration < impactPreview);
  assert.match(picker, /Porción \(g\)/);
  assert.match(picker, /<Scale color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  assert.match(picker, /<Clock color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  assert.match(picker, /<NotebookPen color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  assert.match(picker, /<CalendarDays color=\{tokens\.color\.textMuted\} size=\{18\} \/>/);
  assert.match(picker, /<Text style=\{styles\.compactFieldLabel\}>Porción \(g\)<\/Text>/);
  assert.match(picker, /style=\{styles\.compactFieldInput\} value=\{quantity\}/);
  assert.doesNotMatch(picker, /setQuantity\(value\); setPreview\(null\)/);
  assert.match(picker, /setPreviewPayloadKey\(payloadKey\)/);
  assert.match(picker, /disabled=\{!configurationValid \|\| previewing \|\| previewPayloadKey !== payloadKey\}/);
  assert.match(picker, /style=\{styles\.previewHeading\}/);
  assert.match(picker, /previewHeading: \{[^}]*justifyContent: "space-between"[^}]*width: "100%"/);
  assert.doesNotMatch(picker, /Actualizando previsualización/);
  assert.match(picker, /Hora \(HH:MM\)/);
  assert.match(picker, /style=\{styles\.configurationDivider\}/);
  assert.match(picker, /accessibilityLabel=\{noteEditing \? "Ocultar edición de nota" : "Editar nota"\}/);
  assert.match(picker, /noteEditing \? <TextInput/);
  assert.match(picker, /configurationSticky: \{[^}]*marginHorizontal: -tokens\.spacing\.screen[^}]*paddingHorizontal: tokens\.spacing\.screen/);
  assert.match(picker, /height: 34[^}]*width: 34/);
  assert.doesNotMatch(picker, /function toggleDay\(day: number\) \{[^}]*setPreview\(null\)/s);
  assert.match(picker, /day_numbers/);
  assert.match(picker, /confirm_replacements/);
  assert.match(picker, /Confirmar reemplazos/);
  assert.match(picker, /PickerPreview/);
  assert.match(picker, /dailyplan_meal_id: relationId/);
  assert.match(picker, /meal_food_id: relationId/);
  assert.match(picker, /Reemplazar alimento/);
  assert.match(picker, /target\.panel\.foods\.find\(\(item\) => item\.relation_id === relationId\)/);
  assert.match(picker, /setQuantity\(String\(relation\.quantity\)\)/);
  assert.match(picker, /const detailHref = returnTo \?\?/);
  assert.match(picker, /pickerConfigureHref\(kind, \{ contextDailyPlanId, contextDailyPlanMealId, dayNumber: initialDayNumber, relationId, returnTo/);
  assert.match(picker, /dailyplan_id: contextDailyPlanId/);
  assert.match(picker, /dailyplan_meal_id: contextDailyPlanMealId/);
  assert.doesNotMatch(picker, /protein\s*\*\s*4|carbs\s*\*\s*4|fat\s*\*\s*9/);

  const cardAction = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-card-action.tsx"),
    "utf8",
  );
  assert.match(cardAction, /accessibilityLabel=\{`\$\{label\}: \$\{subject\}`\}/);
  assert.match(cardAction, /backgroundColor: tokens\.color\.textMain/);
  assert.match(cardAction, /borderRadius: tokens\.radius\.pill/);
  assert.match(cardAction, /minHeight: 38/);

  const entryTabs = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-entry-tabs.tsx"),
    "utf8",
  );
  assert.match(entryTabs, /styles\.entryTabsBar/);
  assert.match(entryTabs, /styles\.entryTabActive/);
  assert.match(entryTabs, /icon: Bookmark/);
  assert.match(entryTabs, /icon: Plus/);
  assert.match(entryTabs, /entryTab: \{[^}]*flex: 1/);
  assert.match(entryTabs, /borderRadius: tokens\.radius\.pill/);
  assert.match(entryTabs, /backgroundColor: tokens\.color\.textMain/);
  assert.match(entryTabs, /Mi librería/);

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
  assert.match(configureRoute, /contextDailyPlanId=\{Number\(contextDailyPlanId\) \|\| undefined\}/);
  assert.match(configureRoute, /animation: "slide_from_right"/);

  const resultCard = await readFile(
    path.resolve(process.cwd(), "src/components/pickers/picker-result-card.tsx"),
    "utf8",
  );
  assert.match(resultCard, /Comida resultante/);
  assert.match(resultCard, /Plan diario resultante/);
  assert.match(resultCard, /preview\.selection\.entity === "food"/);
  assert.match(resultCard, /projectedMeal\.foods\.map\(foodPanelItem\)/);
  assert.match(resultCard, /ProgramDayComparisonPanels/);
  assert.match(resultCard, /result\.entity === "week" && week/);
  assert.match(resultCard, /<EntityCard entity="program" eyebrow="Resultado proyectado" title=\{result\.name\}>/);
  assert.match(resultCard, /<EntityCardPanelSlot>/);
  assert.match(resultCard, /result\.panel\.foods\.map\(foodPanelItem\)/);
  assert.match(resultCard, /result\.panel\.meals\.map\(mealPanelItem\)/);
  assert.match(resultCard, /projectedLabel: item\.projected_label/);

  const foodRoute = await readFile(path.resolve(process.cwd(), "src/app/pickers/food-to-meal.tsx"), "utf8");
  assert.match(foodRoute, /mealFoodId/);
  assert.match(foodRoute, /relationId=\{relationId\}/);

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
  assert.match(detail, /pickerHref\("food-to-meal", \{ mealFoodId: food\.relationId, mealId: item\.id, \.\.\.\(hasMealTimeContext/);
  assert.match(detail, /dailyPlanMealId: contextDailyPlanMealId/);

  const panels = await readFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  assert.match(panels, /FoodEditPanel/);
  assert.match(panels, /MealEditPanel/);
  assert.match(panels, /label: "Editar"/);
  assert.match(panels, /Guardar orden/);
  assert.match(panels, /label=\{`Reemplazar \$\{item\.name\}`\}/);
  assert.match(panels, /editing\.onReplace\(item\)/);

  const program = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"), "utf8");
  const assignedPlan = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"), "utf8");
  assert.match(program, /onAssignDailyPlan/);
  assert.match(assignedPlan, /Reemplazar plan diario/);
  assert.match(assignedPlan, /Quitar plan diario/);
  assert.match(program, /allowEmptySelection/);
});
