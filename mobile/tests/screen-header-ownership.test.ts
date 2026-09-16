import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

async function tsxFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const entryPath = path.join(directory, entry.name);
    return entry.isDirectory() ? tsxFiles(entryPath) : entry.name.endsWith(".tsx") ? [entryPath] : [];
  }));
  return nested.flat();
}

test("vertical scroll containers hide their system indicator", async () => {
  for (const file of await tsxFiles(path.resolve(process.cwd(), "src"))) {
    const contents = await readFile(file, "utf8");
    const containers = contents.match(/<(?:ScrollView|NestableScrollContainer)(?:\s|\/)[\s\S]*?(?<!=)>/g) ?? [];
    for (const container of containers) {
      if (/\shorizontal(?:\s|=|>)/.test(container)) continue;
      assert.match(container, /showsVerticalScrollIndicator=\{false\}/, `${path.relative(process.cwd(), file)} has a visible vertical scroll indicator`);
    }
  }
});

test("Screen has one implementation and never overrides externally owned headers", async () => {
  const layout = await source("src/components/ui/layout.tsx");
  const primitives = await source("src/components/ui/primitives.tsx");
  const feedback = await source("src/components/ui/feedback.tsx");

  assert.match(layout, /headerMode\?: "automatic" \| "preserve"/);
  assert.match(layout, /if \(headerMode === "preserve"\) return undefined;[\s\S]*setHeaderPresentation/);
  assert.match(layout, /onScroll=\{\(event\) => setCompactIdentityVisible\(isHeaderIdentityVisible\(event\.nativeEvent\.contentOffset\.y\)\)\}/);
  assert.equal((layout.match(/export function Screen/g) ?? []).length, 1);
  assert.doesNotMatch(primitives, /export function Screen/);
  assert.match(primitives, /import \{ Screen \} from "\.\/layout";[\s\S]*export \{ Screen \}/);
  assert.match(primitives, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
  assert.match(feedback, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
});

test("compact header identities use a short transition", async () => {
  const navigation = await source("src/components/navigation/app-navigation.tsx");
  assert.equal((navigation.match(/duration: 90/g) ?? []).length, 2);
});

test("compact header identities appear only after twelve scroll points", async () => {
  const threshold = await source("src/components/navigation/header-scroll.ts");
  assert.match(threshold, /HEADER_IDENTITY_SCROLL_THRESHOLD = 12/);
  assert.match(threshold, /return offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD/);
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
  assert.match(comparator, /scrollHeader=\{<SectionPageHeader countLabel="comparaciones" section="comparator" title="Comparador" \/>\}/);
  assert.match(comparator, /stickyHeader=\{<ComparisonKindTabs counts=\{counts\}/);
  assert.match(comparator, /stickyHeaderStyle=\{styles\.dashboardStickyHeader\}/);
  assert.match(comparator, /<DistributedTabBar<ComparisonKind>/);
  assert.match(comparator, /identityVisible: compactHeaderVisible[\s\S]*title: "Comparador"/);
  assert.match(comparator, /dashboardStickyHeader: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assert.match(comparator, /builderTabs: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assert.match(comparator, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assert.doesNotMatch(comparator, /<SectionPageHeader count=\{page\?\.total\}/);

  const assistant = await source("src/app/assistant/index.tsx");
  assert.match(assistant, /activeSection === "chats" \? "Acciones de Chats" : "Acciones de Propuestas"/);
  assert.match(assistant, /<AssistantSectionTabs activeSection=\{activeSection\} counts=\{counts\} onChange=\{setActiveSection\} \/>/);
  assert.match(assistant, /<AssistantListActions[\s\S]*activeSection=\{activeSection\}/);
  assert.match(assistant, /scrollHeader=\{scrollHeader\}/);
  assert.match(assistant, /stickyHeader=\{<AssistantSectionTabs/);
  assert.match(assistant, /const scrollHeader = \([\s\S]*<AssistantCreditBalance/);
  assert.doesNotMatch(assistant, /const stickyHeader = \([\s\S]*<AssistantCreditBalance/);
  assert.match(assistant, /stickyHeaderStyle=\{styles\.stickyHeader\}/);
  assert.match(assistant, /identityVisible: compactHeaderVisible/);
  assert.match(assistant, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assert.match(assistant, /const scrollHeader = \([\s\S]*<SectionPageHeader countLabel="elementos" section="chat" title="Asistente AI" \/>/);
  assert.match(assistant, /stickyHeader: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assert.doesNotMatch(assistant, /<SectionPageHeader count=/);
  assert.doesNotMatch(assistant, /disabled: !page\.availability\.is_available/);
  assert.doesNotMatch(assistant, /<Button[^>]*label="Nuevo chat"/);

  const inbox = await source("src/app/inbox.tsx");
  assert.match(inbox, /setHeaderPresentation\(\{ identityVisible: compactHeaderVisible, mode: "default", title: "Inbox" \}\)/);
  assert.match(inbox, /isHeaderIdentityVisible\(nativeEvent\.contentOffset\.y\)/);

  const libraryList = await source("src/components/libraries/library-list-screen.tsx");
  assert.match(libraryList, /mode: "library-list"[\s\S]*identityVisible: compactHeaderVisible/);
  assert.match(libraryList, /isHeaderIdentityVisible\(nativeEvent\.contentOffset\.y\)/);

  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");
  assert.match(libraryDetail, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assert.doesNotMatch(libraryDetail, /subtitle: "Mis librerías"/);
  assert.match(libraryDetail, /<ProgramDetailPreview[\s\S]*onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);

  const calendarizedDay = await source("src/app/program/days/[id].tsx");
  assert.match(calendarizedDay, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assert.doesNotMatch(calendarizedDay, /subtitle: "Mi programa activo"/);

  const calendarizedMeal = await source("src/app/program/days/[id]/meals/[mealKey].tsx");
  assert.match(calendarizedMeal, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assert.doesNotMatch(calendarizedMeal, /subtitle: "Mi programa activo"/);

  const proposals = await source("src/app/proposals/index.tsx");
  assert.match(proposals, /<Redirect href=\{\{ pathname: "\/assistant", params: \{ section: "proposals" \} \}\} \/>/);

  const proposalDetail = await source("src/app/proposals/[id].tsx");
  assert.match(proposalDetail, /fallback: "\/assistant\?section=proposals" as Href, mode: "back", title: "Detalle de propuesta"/);
  assert.match(proposalDetail, /<Screen headerMode="preserve">/);

  const creditBalance = await source("src/components/assistant/assistant-credit-balance.tsx");
  assert.match(creditBalance, /<Card style=\{styles\.card\}>/);
  assert.doesNotMatch(creditBalance, /Saldo de créditos|Sparkles/);
  assert.match(creditBalance, /\{availability\.available_credits\}<\/Text> créditos disponibles/);
  assert.match(creditBalance, /availability\.available_credits/);
  assert.match(creditBalance, /marginBottom: tokens\.spacing\.sm/);
  assert.match(creditBalance, /borderRadius: tokens\.radius\.md/);
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
