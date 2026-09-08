import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("Screen has one implementation and never overrides externally owned headers", async () => {
  const layout = await source("src/components/ui/layout.tsx");
  const primitives = await source("src/components/ui/primitives.tsx");
  const feedback = await source("src/components/ui/feedback.tsx");

  assert.match(layout, /headerMode\?: "automatic" \| "preserve"/);
  assert.match(layout, /if \(headerMode === "preserve"\) return undefined;[\s\S]*setHeaderPresentation/);
  assert.equal((layout.match(/export function Screen/g) ?? []).length, 1);
  assert.doesNotMatch(primitives, /export function Screen/);
  assert.match(primitives, /import \{ Screen \} from "\.\/layout";[\s\S]*export \{ Screen \}/);
  assert.match(primitives, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
  assert.match(feedback, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
});

test("screens that own global navigation preserve their header through content and loading states", async () => {
  for (const relativePath of [
    "src/app/comparator/index.tsx",
    "src/app/assistant/index.tsx",
    "src/app/program/activate.tsx",
    "src/app/program/history.tsx",
    "src/app/program/index.tsx",
    "src/app/today.tsx",
  ]) {
    const screen = await source(relativePath);
    assert.match(screen, /useHeaderPresentation/);
    assert.match(screen, /<Screen[\s\S]*headerMode="preserve"/);
  }

  const compositionPicker = await source("src/components/pickers/composition-picker-screen.tsx");
  assert.match(compositionPicker, /useHeaderPresentation/);
  assert.match(compositionPicker, /setHeaderPresentation\(\{ action: \{ label: "Cancelar"/);
  assert.match(compositionPicker, /return \(\) => setHeaderPresentation\(\{ mode: "default" \}\)/);
  assert.match(compositionPicker, /<SafeAreaView edges=\{\["left", "right"\]\}/);

  const comparator = await source("src/app/comparator/index.tsx");
  assert.match(comparator, /mode: "back", title: savedId \? "Editar comparación" : "Nueva comparación"/);
  assert.match(comparator, /action: \{ label: "Cancelar", onPress: cancel \}/);
  assert.doesNotMatch(comparator, /title=\{savedId \? "Editar Comparación" : "Nueva Comparación"\}/);
  assert.match(comparator, /<View style=\{styles\.builderTabs\}>[\s\S]*<ComparisonKindTabs kind=\{kind\} onChange=\{changeKind\} \/>[\s\S]*<Screen headerMode="preserve">/);

  const assistant = await source("src/app/assistant/index.tsx");
  assert.match(assistant, /activeSection === "chats" \? "Acciones de Chats" : "Acciones de Propuestas"/);
  assert.match(assistant, /<AssistantSectionTabs activeSection=\{activeSection\} counts=\{counts\} onChange=\{setActiveSection\} \/>/);
  assert.match(assistant, /<AssistantListActions[\s\S]*activeSection=\{activeSection\}/);
  assert.match(assistant, /stickyHeader=\{stickyHeader\}/);
  assert.match(assistant, /scrollHeader=\{<SectionPageHeader countLabel="elementos" section="chat" title="Asistente AI" \/>\}/);
  assert.doesNotMatch(assistant, /<SectionPageHeader count=/);
  assert.doesNotMatch(assistant, /disabled: !page\.availability\.is_available/);
  assert.doesNotMatch(assistant, /<Button[^>]*label="Nuevo chat"/);

  const proposals = await source("src/app/proposals/index.tsx");
  assert.match(proposals, /<Redirect href=\{\{ pathname: "\/assistant", params: \{ section: "proposals" \} \}\} \/>/);

  const tabs = await source("src/components/assistant/assistant-section-tabs.tsx");
  assert.match(tabs, /<PanelTabs/);
  assert.match(tabs, /accessibilityLabel="Secciones del Asistente AI"/);
  assert.match(tabs, /counts\[section\.key\]/);
  assert.doesNotMatch(tabs, /StyleSheet|Pressable/);
  assert.doesNotMatch(tabs, /useRouter|router\.replace|href:/);

  const product = await source("src/components/ui/product.tsx");
  assert.match(product, /export function PanelTabs/);
  assert.match(product, /tab: \{[^}]*flex: 1[^}]*justifyContent: "center"[^}]*minHeight: 44/);
  assert.match(product, /<Text style=\{\[styles\.tabText, selected && styles\.tabTextSelected\]\}>\{tab\.label\}<\/Text>[\s\S]*styles\.tabCount/);

  const actions = await source("src/components/assistant/assistant-list-actions.tsx");
  assert.match(actions, /activeSection === "chats"/);
  assert.match(actions, /label="Nuevo chat"/);
  for (const label of ["Ver todas", "Ver pendientes", "Ver aprobadas", "Ver aplicadas", "Ver rechazadas"]) {
    assert.match(actions, new RegExp(label));
  }
});
