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
    "src/app/proposals/[id].tsx",
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
  assert.match(comparator, /<SectionPageHeader countLabel="comparaciones" section="comparator" title="Comparador" \/>/);
  assert.match(comparator, /<ComparisonKindTabs counts=\{counts\}/);
  assert.match(comparator, /<ScrollableTabBar<ComparisonKind>/);
  assert.doesNotMatch(comparator, /<SectionPageHeader count=\{page\?\.total\}/);

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

  const proposalDetail = await source("src/app/proposals/[id].tsx");
  assert.match(proposalDetail, /fallback: "\/assistant\?section=proposals" as Href, mode: "back", title: "Detalle de propuesta"/);
  assert.match(proposalDetail, /<Screen headerMode="preserve">/);

  const creditBalance = await source("src/components/assistant/assistant-credit-balance.tsx");
  assert.match(creditBalance, /<Card style=\{styles\.card\}>/);
  assert.match(creditBalance, /Saldo de créditos/);
  assert.match(creditBalance, /availability\.available_credits/);
  assert.match(creditBalance, /marginBottom: tokens\.spacing\.sm/);
  assert.match(assistant, /<AssistantCreditBalance availability=\{chatPage\.availability\} \/>/);

  const tabs = await source("src/components/assistant/assistant-section-tabs.tsx");
  assert.match(tabs, /MessageCircle/);
  assert.match(tabs, /ClipboardCheck/);
  assert.match(tabs, /DistributedTabBar<AssistantSection>/);
  assert.match(tabs, /count: counts\.chats/);
  assert.match(tabs, /count: counts\.proposals/);
  assert.doesNotMatch(tabs, /PanelTabs/);
  assert.doesNotMatch(tabs, /StyleSheet\.create/);
  assert.doesNotMatch(tabs, /useRouter|router\.replace|href:/);

  const actions = await source("src/components/assistant/assistant-list-actions.tsx");
  assert.match(actions, /activeSection === "chats"/);
  assert.match(actions, /label="Nuevo chat"/);
  for (const label of ["Ver todas", "Ver pendientes", "Ver aprobadas", "Ver aplicadas", "Ver rechazadas"]) {
    assert.match(actions, new RegExp(label));
  }
});
