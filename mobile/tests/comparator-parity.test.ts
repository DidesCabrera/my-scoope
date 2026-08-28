import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the mobile comparator preserves web slot and metric comparison dynamics", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  const result = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");

  assert.match(screen, /function emptySlots\(\)/);
  assert.match(screen, /addSlot/);
  assert.match(screen, /removeSlot/);
  assert.match(screen, /slots\.flatMap/);
  assert.match(screen, /function ComparatorDashboard/);
  assert.match(screen, /function ComparisonKindTabs/);
  assert.match(screen, /accessibilityRole="tablist"/);
  assert.match(screen, /value: "foods" as const, icon: Carrot, label: "Alimentos"/);
  assert.match(screen, /value: "meals" as const, icon: Utensils, label: "Comidas"/);
  assert.match(screen, /value: "dailyplans" as const, icon: ClipboardList, label: "Planes"/);
  assert.match(screen, /foods: "food"/);
  assert.match(screen, /meals: "meal"/);
  assert.match(screen, /dailyplans: "dailyPlan"/);
  assert.match(screen, /<EntityCard[\s\S]*entity=\{entity\}[\s\S]*eyebrow=\{`\$\{/);
  assert.match(screen, /slot\.option\?\.nutrition \? \([\s\S]*<NutritionKpiSection variant="nested" \{\.\.\.libraryNutrition\(slot\.option\.nutrition\)\} \/>/);
  assert.ok(screen.indexOf('<NutritionKpiSection variant="nested"') < screen.indexOf('<Button label={slot.option ? "Cambiar selección" : "Seleccionar"}'));
  assert.doesNotMatch(screen, /styles\.slotLabel|styles\.slotName|styles\.slotIdentity/);
  assert.match(screen, /actionLabel="Crear nueva comparación"/);
  assert.match(screen, /router\.setParams\(\{ kind: nextKind \}\)/);
  assert.match(screen, /actionLabel="Crear nueva comparación"[\s\S]*onAction=\{\(\) => router\.push\(creationHref\(kind\)\)\}/);
  assert.match(screen, /create: "1", kind/);
  assert.doesNotMatch(screen, /title=\{savedId \? "Editar Comparación" : "Nueva Comparación"\}/);
  assert.doesNotMatch(screen, /ChoiceRow|label="Tipo de comparación"/);
  assert.match(screen, /<View style=\{styles\.builderRoot\}>[\s\S]*<View style=\{styles\.builderTabs\}>[\s\S]*<ComparisonKindTabs kind=\{kind\} onChange=\{changeKind\} \/>[\s\S]*<Screen headerMode="preserve">/);
  assert.match(screen, /const cancel = \(\) => \{ if \(router\.canGoBack\(\)\) router\.back\(\); else router\.replace\(fallback\); \}/);
  assert.match(screen, /action: \{ label: "Cancelar", onPress: cancel \}/);
  assert.match(screen, /action: \{ icon: "plus", label: "Crear una comparación", onPress: \(\) => router\.push\(creationHref\(kind\)\) \}/);
  assert.match(screen, /function ComparatorDashboard[\s\S]*<Screen headerMode="preserve">/);
  assert.match(navigation, /headerPresentation\.action\.icon === "plus"[\s\S]*<Plus/);
  assert.doesNotMatch(navigation, /comparatorIndexVisible|comparatorKind|useGlobalSearchParams/);
  assert.doesNotMatch(screen, /accessibilityRole="checkbox"/);
  assert.match(result, /result\.metrics\.map/);
  assert.match(result, /metric\.bars\.map/);
  assert.match(result, /relative_percentage/);
});

test("comparison selections use the shared picker pattern and return to the original slot", async () => {
  const builder = await readFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  const selector = await readFile(path.resolve(process.cwd(), "src/app/comparator/select.tsx"), "utf8");
  const apiTypes = await readFile(path.resolve(process.cwd(), "src/api/types.ts"), "utf8");
  const transfer = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparator-selection-context.tsx"), "utf8");
  const layout = await readFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");

  assert.match(builder, /pathname: "\/comparator\/select"/);
  assert.match(builder, /slotKey: String\(slotKey\)/);
  assert.match(builder, /const selection = consumeSelection\(\)/);
  assert.match(builder, /slot\.key === selection\.slotKey/);
  assert.doesNotMatch(builder, /activeSlotKey|slotBadge|Cerrar selector|Buscar en tu librería/);

  assert.match(selector, /stickyHeaderIndices=\{\[0\]\}/);
  assert.match(selector, /<PickerEntryTabs/);
  assert.match(selector, /style=\{styles\.searchField\}/);
  assert.match(selector, /\/api\/v1\/comparisons\/options\/\$\{kind\}/);
  assert.match(selector, /import \{ PickerCardAction \} from "@\/components\/pickers\/picker-card-action"/);
  assert.match(selector, /<NutritionEntityCard[\s\S]*actions=\{<PickerCardAction label="Seleccionar"[\s\S]*entity=\{option\.entity\}/);
  assert.match(selector, /nutrition=\{libraryNutrition\(option\.nutrition\)\}/);
  assert.match(selector, /indicators=\{option\.indicators\}/);
  assert.match(selector, /option\.panel\.kind === "foods" \? <FoodPanels/);
  assert.match(selector, /option\.panel\.kind === "meals" \? <MealPanels/);
  assert.doesNotMatch(selector, /<EntityCard|<Card|<EntityIcon|<Button label="Seleccionar"/);
  assert.match(apiTypes, /export type ComparisonOption = Pick<[\s\S]*"id" \| "entity" \| "indicators" \| "name" \| "nutrition" \| "panel" \| "subtitle"/);
  assert.match(selector, /publishSelection\(\{ kind, option, slotKey \}\)/);
  assert.match(selector, /if \(router\.canGoBack\(\)\) router\.back\(\)/);
  assert.match(selector, /setHeaderPresentation\(\{ fallback: returnHref, mode: "back", title: config\.title \}\)/);
  assert.doesNotMatch(selector, /label: "Cancelar"/);
  assert.match(selector, /pathname: "\/libraries\/create"/);

  assert.match(transfer, /pendingSelection = useRef/);
  assert.match(transfer, /pendingSelection\.current = null/);
  assert.match(layout, /<ComparatorSelectionProvider>[\s\S]*<Stack/);
});
