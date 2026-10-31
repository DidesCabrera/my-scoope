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
  expectSource(product, 'expanded && { backgroundColor: `${activeColor}1A`, borderColor: activeColor }');
  expectSource(product, "expanded && styles.entityCardPanelToggleLabelActive");
  expectSource(product, "entityCardPanelToggleLabelActive: { color: tokens.color.textMain }");
  for (const mapping of ["chart: ChartNoAxesCombined", "food: Carrot", "information: Info", "meal: Utensils"]) expectSource(product, mapping);
  expectSource(product, "<Icon color={expanded ? tokens.color.textMain : tokens.color.textMuted} size={14}");
  expectSource(product, 'entityCardPanelToggle: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, height: 34, justifyContent: "center", marginLeft: -6, paddingHorizontal: tokens.spacing.sm }');
  expectSource(product, "entityCardPanelToggleIcon: { marginLeft: 4 }");
  expectSource(product, "entityCardPanelToggleLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold, marginRight: 6 }");
  expectSource(product, 'entityCardAction: { alignItems: "center", borderColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, borderWidth: 1, height: 34, justifyContent: "center", width: 34 }');
  expectSource(product, "<EntityCardActions leading={panelToggle ? <EntityCardPanelToggle");
  expectSource(product, 'entityCardActions: { alignItems: "center", alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between" }');
  expectSource(product, 'entityCardActionGroup: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, marginLeft: "auto", marginRight: -6 }');
  expectSource(nutritionCard, "const [panelExpanded, setPanelExpanded] = useState(true)");
  expectSource(nutritionCard, 'entity === "food" ? "information" : entity === "meal" ? "food" : entity === "program" ? "chart" : "meal"');
  expectSource(nutritionCard, 'entity === "food" || entity === "meal" ? tokens.color.food : entity === "dailyPlan" ? tokens.color.meal : tokens.color.dailyPlan');
  for (const label of ["Más información", "Alimentos", "Comidas", "Semanas"]) expectSource(nutritionCard, label);
  expectSource(nutritionCard, "<EntityCardActions leading={panelToggle}>{actions}</EntityCardActions>");
  expectSource(nutritionCard, "children && (!hasCollapsiblePanel || panelExpanded)");
  expectSource(nutritionCard, "actionsBeforePanel: { marginTop: 2 }");
  expectSource(nutritionCard, "actionsBeforePanelCollapsed: { marginBottom: -2 }");
  expectSource(nutritionCard, "panelAfterActions: { marginTop: 2 }");
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
  expectSource(programCard, "const [metricsExpanded, setMetricsExpanded] = useState(true)");
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
