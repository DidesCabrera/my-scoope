import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import {
  applyComparatorSelection,
  initialComparisonSlots,
} from "../src/components/comparisons/comparison-state";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("comparison builder starts with two independent empty slots", () => {
  const slots = initialComparisonSlots();

  assert.deepEqual(slots, [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ]);
  assert.notEqual(slots[0], slots[1]);
});

test("saved comparison results omit the explanatory snapshot notice", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceDoesNotMatch(source, /fotografía guardada|historical_snapshot|InlineNotice/);
  assertSourceMatch(source, /<ProgramSectionHeader[\s\S]*icon=\{Scale\}[\s\S]*subtitle="Observa las diferencias entre las comidas de la forma que más te acomode\."[\s\S]*title="Resultados de la comparación"/);
  assertSourceDoesNotMatch(source, /SectionTitle/);
});

test("comparison builder presents generated results without a divider", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /<ComparisonResultCards result=\{result\} \/>/);
  assertSourceMatch(source, /<View style=\{styles\.saveAction\}>[\s\S]*<Button label=\{savedId \? "Guardar cambios" : "Guardar comparación"\}[\s\S]*onPress=\{\(\) => void persist\(\)\} \/>/);
  assertSourceMatch(source, /saveAction: \{ marginTop: 40 \}/);
  assertSourceDoesNotMatch(source, /label=\{savedId \? "Guardar cambios" : "Guardar comparación"\}[^>]*variant="secondary"/);
  assertSourceDoesNotMatch(source, /SectionDivider/);
  assertSourceDoesNotMatch(source, /Aún no hay resultado/);
});

test("comparison header creation action offers every comparison kind", async () => {
  const dashboard = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-create-actions.tsx"), "utf8");
  assertSourceMatch(dashboard, /onPress: \(\) => setCreateActionsVisible\(true\)/);
  assertSourceMatch(dashboard, /<ComparisonCreateActions[\s\S]*onSelect=\{\(selectedKind\) => router\.push\(creationHref\(selectedKind\)\)\}/);
  assertSourceMatch(actions, /label="Comparar alimentos"[\s\S]*select\("foods"\)/);
  assertSourceMatch(actions, /label="Comparar comidas"[\s\S]*select\("meals"\)/);
  assertSourceMatch(actions, /label="Comparar planes diarios"[\s\S]*select\("dailyplans"\)/);
  assertSourceMatch(actions, /iconNode=\{<EntityIcon entity="food" size="compact" \/>\}/);
  assertSourceMatch(actions, /iconNode=\{<EntityIcon entity="meal" size="compact" \/>\}/);
  assertSourceMatch(actions, /iconNode=\{<EntityIcon entity="dailyPlan" size="compact" \/>\}/);
});

test("comparison dashboard loads every tab once and switches locally", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /const \[pages, setPages\] = useState<ComparisonPages \| null>\(null\)/);
  assertSourceMatch(source, /limit=50&kind=\$\{item\.value\}/);
  assertSourceMatch(source, /const page = pages\?\.\[kind\] \?\? null/);
  assertSourceMatch(source, /\}, \[apiRequest\]\)/);
  assertSourceMatch(source, /onEdit=\{\(\) => router\.push\(\{ pathname: "\/comparator", params: \{ kind: item\.kind, savedId: String\(item\.id\) \} \}/);
  assertSourceMatch(source, /onRename=\{async \(name\) => \{[\s\S]*method: "PATCH"[\s\S]*await load\(\)/);
  assertSourceDoesNotMatch(source, /item\.value === kind \? 50 : 1/);
});

test("new comparison keeps the kind selected before opening the builder", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceDoesNotMatch(source, /<ComparisonKindTabs kind=\{kind\}/);
  assertSourceDoesNotMatch(source, /function changeKind/);
  assertSourceMatch(source, /useState<ComparisonKind>\(params\.kind === "meals" \|\| params\.kind === "dailyplans" \? params\.kind : "foods"\)/);
});

test("comparison builder actions name the selected entity kind", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /`Seleccionar \$\{entityLabel\}`/);
  assertSourceMatch(source, /`Agregar \$\{kind === "meals" \? "otra" : "otro"\} \$\{entityLabel\}`/);
  assertSourceDoesNotMatch(source, /label=\{slot\.option \? "Cambiar selección" : "Seleccionar"\}/);
  assertSourceMatch(source, /icon=\{slot\.option[\s\S]*<RefreshCcw[\s\S]*<Search/);
});

test("comparison action has additional separation from the builder controls", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /<View style=\{styles\.compareAction\}>[\s\S]*label="Comparar"/);
  assertSourceMatch(source, /disabled=\{selectedCount < 2 \|\| result != null\}/);
  assertSourceMatch(source, /function invalidateResult\(\) \{[\s\S]*setResult\(null\)/);
  assertSourceMatch(source, /compareAction: \{ marginTop: 28 \}/);
  assertSourceMatch(source, /<Button[^>]*icon=\{<Plus[^>]*\/>\} label=\{anotherEntityLabel\}/);
});

test("comparison icon actions receive an optical left alignment", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /contentStyle=\{styles\.comparisonButtonContent\}[\s\S]*<RefreshCcw/);
  assertSourceMatch(source, /contentStyle=\{styles\.comparisonButtonContent\} icon=\{<Plus/);
  assertSourceMatch(source, /comparisonButtonContent: \{ transform: \[\{ translateX: -10 \}\] \}/);
});

test("comparison result rows omit numeric position badges", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceDoesNotMatch(source, /positionBadge|positionText|>\{bar\.position\}<\/Text>/);
  assertSourceMatch(source, /const entity = comparisonEntity\(result\.kind\)/);
  assertSourceMatch(source, /<Card accent=\{tokens\.color\[entity\]\} key=\{metric\.key\}>/);
  assertSourceMatch(source, /<Card accent=\{tokens\.color\[entity\]\}>[\s\S]*Distribución macros/);
  assertSourceMatch(source, /<View style=\{styles\.barIdentity\}>[\s\S]*<EntityIcon entity=\{entity\} size="compact" \/>[\s\S]*\{bar\.label\}/);
});

test("comparison percentage bars match the compact progress height", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceMatch(source, /track: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*height: 10/);
  assertSourceMatch(source, /allocationKeys = \["alloc_protein", "alloc_carbs", "alloc_fat"\]/);
  assertSourceMatch(source, /<Text style=\{styles\.metricTitle\}>Distribución macros<\/Text>/);
  assertSourceMatch(source, /backgroundColor: tokens\.color\.protein, flex: Math\.max\(proteinBar\.value, 0\)/);
  assertSourceMatch(source, /backgroundColor: tokens\.color\.carbs, flex: Math\.max\(carbsBar\.value, 0\)/);
  assertSourceMatch(source, /backgroundColor: tokens\.color\.fat, flex: Math\.max\(fatBar\.value, 0\)/);
  assertSourceMatch(source, /<View style=\{styles\.barMeta\}>[\s\S]*styles\.barIdentity[\s\S]*styles\.allocationLegend[\s\S]*styles\.allocationTrack/);
  assertSourceMatch(source, /barRow: \{ gap: tokens\.spacing\.sm \}/);
  assertSourceMatch(source, /bars: \{ gap: tokens\.spacing\.lg \}/);
  assertSourceMatch(source, /allocationValue: \{ fontSize: tokens\.type\.caption/);
  assertSourceMatch(source, /allocationKey: \{ color: tokens\.color\.textMain, fontWeight: tokens\.weight\.regular \}/);
  assertSourceMatch(source, /styles\.allocationKey}>P <\/Text>\{compactPercentage\(proteinBar\.formatted_value\)\}[\s\S]*styles\.allocationKey}>C <\/Text>\{compactPercentage\(carbsBar\.formatted_value\)\}[\s\S]*styles\.allocationKey}>F <\/Text>\{compactPercentage\(fatBar\.formatted_value\)\}/);
  assertSourceMatch(source, /return value\.replace\(\/\\s\+%\$\/, "%"\)/);
  assertSourceDoesNotMatch(source, /styles\.metricUnit/);
});

test("saved comparison detail switches between result cards and entity cards", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  assertSourceMatch(source, /<DistributedTabBar<DetailTab>/);
  assertSourceMatch(source, /<View style=\{styles\.tabsBleed\}>[\s\S]*<DistributedTabBar<DetailTab>/);
  assertSourceMatch(source, /tabsBleed: \{ alignSelf: "stretch", marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  assertSourceMatch(source, /scrollHeader=\{<View style=\{styles\.detailHeader\}>[\s\S]*<AppHeader/);
  assertSourceMatch(source, /stickyHeader=\{<View style=\{styles\.tabsBleed\}>/);
  assertSourceMatch(source, /stickyTabs: \{ paddingTop: tokens\.spacing\.xl \}/);
  assertSourceMatch(source, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assertSourceMatch(source, /identityVisible: compactHeaderVisible/);
  assertSourceMatch(source, /fallback: comparatorHref/);
  assertSourceDoesNotMatch(source, /forceFallback: true/);
  assertSourceMatch(source, /`Comparación \$\{entityTabLabels\[comparison\.kind\]\}`/);
  assertSourceMatch(source, /action: comparisonId != null \? \{ icon: "more", label: "Acciones de comparación"/);
  assertSourceMatch(source, /<SavedComparisonActions/);
  assertSourceMatch(source, /onDelete=\{async \(\) => \{[\s\S]*method: "DELETE"[\s\S]*router\.replace/);
  assertSourceDoesNotMatch(source, /<Button[^>]*label="Editar comparación"|Usar en el Asistente|Volver a guardadas/);
  assertSourceMatch(source, /key: "cards", label: "Cards"/);
  assertSourceMatch(source, /<Rows3[^>]*\/>[^\n]*key: "table", label: "Tabla"/);
  assertSourceMatch(source, /label: entityTabLabels\[kind\]/);
  assertSourceMatch(source, /activeTab === "cards" \? <ComparisonResultCards/);
  assertSourceMatch(source, /activeTab === "table" \? <SavedComparisonPreviewPanels items=\{comparison\.items\} scope=\{entity\} \/>/);
  assertSourceMatch(source, /<ComparisonResultCards hideHeader result=\{comparison\} \/>/);
  assertSourceMatch(source, /<AppHeader[\s\S]*<Chip backgroundColor=\{`\$\{tokens\.color\[entity\]\}1A`\} borderColor=\{tokens\.color\[entity\]\} label=\{`\$\{comparisonItemCount\} \$\{comparisonItemLabel\}`\}/);
  assertSourceMatch(source, /<ComparisonItemsSummary items=\{comparison\.items\} \/>/);
  assertSourceMatch(source, /comparisonItemCount === 1 \? 0 : 1/);
  assertSourceMatch(source, /Promise\.all\(saved\.items\.map\(\(item\) => apiRequest<LibraryItem>/);
  assertSourceMatch(source, /activeTab === "entities" \? entityItems\.map/);
  assertSourceMatch(source, /<LibraryCard apiRequest=\{apiRequest\} interactive=\{false\} item=\{item\}[^>]*navigable/);
});

test("picker result updates only its destination without mutating prior state", () => {
  const original = initialComparisonSlots();
  const option = { id: 42, name: "Avena" };

  const updated = applyComparatorSelection(original, { slotKey: 2, option });

  assert.equal(original[1]?.option, null);
  assert.equal(updated[0], original[0]);
  assert.deepEqual(updated[1], { key: 2, option, quantity: "100" });
});

test("stale picker result leaves slots unchanged", () => {
  const original = initialComparisonSlots();

  const updated = applyComparatorSelection(original, {
    slotKey: 999,
    option: { id: 7, name: "Arroz" },
  });

  assert.deepEqual(updated, original);
});
