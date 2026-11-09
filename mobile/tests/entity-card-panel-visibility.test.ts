import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

function expectSource(contents: string, fragment: string) {
  const normalizedContents = contents.replace(/\s+/g, " ");
  const normalizedFragment = fragment.replace(/\s+/g, " ");
  assert.ok(normalizedContents.includes(normalizedFragment), `Expected source to contain: ${normalizedFragment}`);
}

test("entity cards expose a shared left-aligned panel visibility control", async () => {
  const product = await source("src/components/ui/product.tsx");
  const nutritionCard = await source("src/components/nutrition/nutrition-entity-card.tsx");

  expectSource(product, "export function EntityCardPanelToggle");
  expectSource(product, "accessibilityState={{ expanded }}");
  expectSource(product, 'expanded && { backgroundColor: solidActive ? activeColor : `${activeColor}1A`, borderColor: tokens.color.surfaceCard }');
  assert.equal(/expanded && \{[^}]*borderColor: activeColor/.test(product), false);
  expectSource(product, "expanded && styles.entityCardPanelToggleLabelActive");
  expectSource(product, "entityCardPanelToggleLabelActive: { color: tokens.color.textMain }");
  for (const mapping of ["chart: ChartNoAxesCombined", "food: Carrot", "information: Info", "meal: Utensils", "supplement: Pill"]) expectSource(product, mapping);
  expectSource(product, "<Icon color={expanded ? activeForeground : tokens.color.textMuted} size={14}");
  expectSource(product, 'entityCardPanelToggle: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: 2, height: 32, justifyContent: "center", paddingHorizontal: tokens.spacing.compact }');
  expectSource(product, "entityCardPanelToggleIcon: { marginLeft: 1 }");
  expectSource(product, "entityCardPanelToggleLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, marginRight: 2 }");
  expectSource(product, 'entityCardAction: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, borderWidth: 1, height: 32, justifyContent: "center", width: 32 }');
  expectSource(product, "<EntityCardActions leading={panelToggle ? <EntityCardPanelToggle");
  expectSource(product, 'entityCardActions: { alignItems: "center", alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between", marginHorizontal: -6, marginTop: 6 }');
  expectSource(product, 'entityCardActionGroup: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, marginLeft: "auto" }');
  expectSource(nutritionCard, "initialPanelExpanded = false");
  expectSource(nutritionCard, "const [panelExpanded, setPanelExpanded] = useState(initialPanelExpanded)");
  expectSource(nutritionCard, "const [foodsPanelExpanded, setFoodsPanelExpanded] = useState(false)");
  expectSource(nutritionCard, 'entity === "food" ? "information" : entity === "meal" || entity === "preparation" ? "food" : entity === "program" ? "chart" : "meal"');
  expectSource(nutritionCard, 'entity === "food" || entity === "meal" || entity === "preparation" ? tokens.color.food : entity === "dailyPlan" ? tokens.color.meal : tokens.color.dailyPlan');
  for (const label of ["Más información", "Alimentos", "Comidas", "Semanas"]) expectSource(nutritionCard, label);
  expectSource(nutritionCard, "<EntityCardActions leading={panelToggles}>{actions}</EntityCardActions>");
  expectSource(nutritionCard, "hasCollapsiblePanel && anyPanelExpanded");
  expectSource(nutritionCard, "panelExpanded ? <EntityCardPanelSlot>{children}</EntityCardPanelSlot>");
  expectSource(nutritionCard, "actionsBeforePanel: { marginTop: 2 }");
  expectSource(nutritionCard, "actionsBeforePanelCollapsed: { marginBottom: -2 }");
  expectSource(nutritionCard, "panelAfterActions: { marginTop: 2 }");
});

test("picker selection actions match the panel toggle height without changing full-width actions", async () => {
  const pickerAction = await source("src/components/pickers/picker-card-action.tsx");
  expectSource(pickerAction, "minHeight: 32, minWidth: 112, paddingHorizontal: tokens.spacing.compact");
  expectSource(pickerAction, 'actionMutedFullWidth: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceMuted, minHeight: 38');
  expectSource(pickerAction, 'actionCardFullWidth: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceCard, minHeight: 38');
});

test("picker list cards expose nutrition and ingredient panels without changing selection", async () => {
  const [picker, foodPanel, preparationCard] = await Promise.all([
    source("src/components/pickers/composition-picker-screen.tsx"),
    source("src/components/pickers/picker-food-nutrition-panel.tsx"),
    source("src/components/preparations/preparation-picker-card.tsx"),
  ]);
  expectSource(picker, 'collapsiblePanel={showPanels && (option.entity === "food" || hasMealContents)}');
  expectSource(picker, '<PickerFoodNutritionPanel foodId={option.id}');
  expectSource(picker, '<PickerCardAction label={actionLabel} onPress={onAction} subject={option.name} />');
  expectSource(foodPanel, '`/api/v1/library/foods/${foodId}`');
  expectSource(foodPanel, '<FoodNutritionPanel facts={libraryFoodNutritionFacts(baseNutrition, detail?.food_nutrition)} portion={portion} />');
  expectSource(preparationCard, 'collapsiblePanel');
  expectSource(preparationCard, '<FoodPanels items={detail.ingredients.map');
  expectSource(preparationCard, '<PickerCardAction label={actionLabel} onPress={onAction} subject={detail.name} />');
});

test("meal picker cards keep the library's food and preparation rows behind a collapsed panel", async () => {
  const [picker, libraryPanels, libraryCard] = await Promise.all([
    source("src/components/pickers/composition-picker-screen.tsx"),
    source("src/components/libraries/entity-panels.tsx"),
    source("src/components/libraries/library-card.tsx"),
  ]);
  expectSource(picker, 'const hasMealContents = option.entity === "meal" && option.panel?.kind === "foods"');
  expectSource(picker, 'collapsiblePanel={showPanels && (option.entity === "food" || hasMealContents)}');
  expectSource(picker, '<SharedFoodPanels items={mealComponents} nestedScroll onOpenItem={openMealComponent} showEditTab={false} />');
  expectSource(picker, 'showPanels={kind !== "dailyplan-to-program"}');
  expectSource(libraryPanels, '...(panel.preparations ?? []).map((preparation) => preparationPanelItem(preparation, nutrition))');
  expectSource(libraryCard, 'mealFoodPanelItems(item.panel, item.nutrition)');
  expectSource(picker, 'mealFoodPanelItems(option.panel, option.nutrition)');
});

test("library entity cards collapse their corresponding detail panels", async () => {
  const libraryActions = await source("src/components/libraries/library-actions.tsx");
  const libraryCard = await source("src/components/libraries/library-card.tsx");
  const foodPanel = await source("src/components/panels/food-nutrition-panel.tsx");
  const programCard = await source("src/components/libraries/program-child-card.tsx");

  expectSource(libraryCard, "<NutritionEntityCard");
  expectSource(libraryCard, "collapsiblePanel");
  expectSource(libraryActions, "<MoreHorizontal color={tokens.color.textMuted} size={19}");
  expectSource(libraryCard, "<ChevronRight color={tokens.color.textMuted} size={19}");
  expectSource(libraryCard, 'item.entity === "food" ? <FoodNutritionPanel');
  for (const nutrient of ["Información nutricional", "NutritionFactsTable"]) expectSource(foodPanel, nutrient);
  expectSource(programCard, "const [metricsExpanded, setMetricsExpanded] = useState(false)");
  expectSource(programCard, "<EntityCardActions leading={<EntityCardPanelToggle");
  expectSource(programCard, '<EntityCardAction label="Más acciones"');
  expectSource(programCard, "<MoreHorizontal color={tokens.color.textMuted} size={19} strokeWidth={2.2}");
  expectSource(programCard, '<EntityCardAction label="Ver programa" onPress={onOpen} role="link"');
  expectSource(programCard, "<ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2}");
  expectSource(programCard, '<EntityCardPanelToggle activeColor={tokens.color.dailyPlan} expanded={metricsExpanded} icon="chart"');
  expectSource(programCard, 'text="Semanas"');
  expectSource(programCard, "metricsExpanded ? <ProgramMetricPreview");
  expectSource(programCard, "footer: { marginTop: 2 }");
  expectSource(programCard, "footerCollapsed: { marginBottom: -2 }");
  expectSource(programCard, "footerExpanded: { marginBottom: 2 }");
});

test("daily-plan cards expose an adjacent foods-panel control backed by their existing food data", async () => {
  const nutritionCard = await source("src/components/nutrition/nutrition-entity-card.tsx");
  const dailyPlanCards = await Promise.all([
    "src/components/libraries/library-card.tsx",
    "src/components/calendarization/pinned-daily-plan-card.tsx",
    "src/components/calendarization/calendarized-daily-plan-card.tsx",
    "src/components/libraries/program-daily-plan-preview.tsx",
  ].map(source));

  expectSource(nutritionCard, 'entity === "dailyPlan" && Boolean(dailyPlanFoodsPanel)');
  expectSource(nutritionCard, '<EntityCardPanelToggle activeColor={tokens.color.food} expanded={foodsPanelExpanded} icon="food"');
  expectSource(nutritionCard, 'solidActive={hasDailyPlanFoodsPanel || entity === "food" || entity === "meal" || entity === "preparation"}');
  expectSource(nutritionCard, 'solidActive text="Alimentos"');
  expectSource(nutritionCard, 'text="Alimentos"');
  expectSource(nutritionCard, "if (shouldExpand && hasDailyPlanFoodsPanel) setFoodsPanelExpanded(false)");
  expectSource(nutritionCard, "if (shouldExpand) setPanelExpanded(false)");
  expectSource(nutritionCard, "<View style={styles.panelToggleGroup}>{panelToggle}{supplementPanelToggle}{foodsPanelToggle}</View>");
  expectSource(nutritionCard, "hasDailyPlanFoodsPanel && foodsPanelExpanded ? <EntityCardPanelSlot>{dailyPlanFoodsPanel}</EntityCardPanelSlot>");
  expectSource(nutritionCard, 'panelToggleGroup: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.compact }');
  for (const card of dailyPlanCards) expectSource(card, "dailyPlanFoodsPanel=");
});

test("only today's home plan cards start with their panels expanded", async () => {
  const today = await source("src/app/today.tsx");
  const calendarizedCard = await source("src/components/calendarization/calendarized-daily-plan-card.tsx");
  const pinnedCard = await source("src/components/calendarization/pinned-daily-plan-card.tsx");

  assert.equal(today.match(/initialPanelExpanded/g)?.length, 2);
  expectSource(calendarizedCard, "initialPanelExpanded = false");
  expectSource(calendarizedCard, "initialPanelExpanded={initialPanelExpanded}");
  expectSource(pinnedCard, "initialPanelExpanded = false");
  expectSource(pinnedCard, "initialPanelExpanded={initialPanelExpanded}");
});

test("in-progress meal and daily-plan cards use the shared collapsible panel", async () => {
  for (const relativePath of [
    "src/components/calendarization/calendarized-daily-plan-card.tsx",
    "src/components/calendarization/pinned-daily-plan-card.tsx",
    "src/components/libraries/entity-panels.tsx",
    "src/components/libraries/program-daily-plan-preview.tsx",
    "src/app/program/days/[id].tsx",
  ]) {
    const card = await source(relativePath);
    expectSource(card, "<NutritionEntityCard");
    expectSource(card, "collapsiblePanel");
  }
});
