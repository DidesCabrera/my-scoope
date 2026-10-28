import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch } from "./support/source-contract";

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
      assertSourceMatch(container, /showsVerticalScrollIndicator=\{false\}/, `${path.relative(process.cwd(), file)} has a visible vertical scroll indicator`);
    }
  }
});

test("Screen has one implementation and never overrides externally owned headers", async () => {
  const layout = await source("src/components/ui/layout.tsx");
  const primitives = await source("src/components/ui/primitives.tsx");
  const feedback = await source("src/components/ui/feedback.tsx");

  assertSourceMatch(layout, /headerMode\?: "automatic" \| "preserve"/);
  assertSourceMatch(layout, /if \(headerMode === "preserve"\) return undefined;[\s\S]*setHeaderPresentation/);
  assertSourceMatch(layout, /onScroll=\{\(event\) => setCompactIdentityVisible\(nextHeaderIdentityVisibility\(event\.nativeEvent\.contentOffset\.y, compactHeaderVisibleRef\.current\)\)\}/);
  assertSourceMatch(layout, /if \(compactHeaderVisibleRef\.current === visible\) return/);
  assertSourceMatch(layout, /BOTTOM_SPACING = 96/);
  assertSourceMatch(layout, /paddingBottom: BOTTOM_SPACING/);
  assertSourceMatch(layout, /scroll\?: boolean \| "auto"/);
  assertSourceMatch(layout, /automaticallyAdjustKeyboardInsets/);
  assertSourceMatch(layout, /keyboardDismissMode=\{Platform\.OS === "ios" \? "interactive" : "on-drag"\}/);
  assertSourceMatch(layout, /screenContent: \{ flexGrow: 1/);
  assertSourceDoesNotMatch(layout, /screenContent: \{ flex: 1/);
  assert.equal((layout.match(/export function Screen/g) ?? []).length, 1);
  assertSourceDoesNotMatch(primitives, /export function Screen/);
  assertSourceMatch(primitives, /import \{ Screen \} from "\.\/layout";[\s\S]*export \{ Screen \}/);
  assertSourceDoesNotMatch(primitives, /export function LoadingState/);
  assertSourceMatch(primitives, /export \{ LoadingState \}/);
  assertSourceMatch(feedback, /const viewportOffset = headerVisible \? -\(GLOBAL_HEADER_HEIGHT \+ insets\.top\) \/ 2 : 0/);
  assertSourceMatch(feedback, /<Screen scroll=\{false\} contentStyle=\{\[styles\.loadingState, \{ transform: \[\{ translateY: viewportOffset \}\] \}\]\} headerMode="preserve">/);
  assertSourceMatch(feedback, /mode === "content"[\s\S]*styles\.loadingContent/);
});

test("header navigation and action icons use muted text color", async () => {
  const navigation = await source("src/components/navigation/app-navigation.tsx");
  for (const icon of ["ChevronLeft", "PanelRight", "Plus", "MoreHorizontal", "Pin", "CalendarClock", "Clock3"]) {
    assertSourceDoesNotMatch(navigation, new RegExp(`<${icon} color=\\{tokens\\.color\\.textMain\\}`));
  }
  assertSourceMatch(navigation, /<PanelRight color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(navigation, /<MoreHorizontal color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(navigation, /menuSectionLabel: \{[^}]*fontWeight: tokens\.component\.eyebrow\.fontWeight/);
});

test("compact header identities use a short transition", async () => {
  const navigation = await source("src/components/navigation/app-navigation.tsx");
  assert.equal((navigation.match(/duration: 90/g) ?? []).length, 1);
  assertSourceMatch(navigation, /function useHeaderIdentityProgress\(visible: boolean\)/);
  assertSourceMatch(navigation, /const animation = Animated\.timing\(progress/);
  assertSourceMatch(navigation, /return \(\) => animation\.stop\(\)/);
});

test("header presentation updates do not rerender setter-only screens or the sidebar", async () => {
  const navigation = await source("src/components/navigation/app-navigation.tsx");
  assertSourceMatch(navigation, /const HeaderPresentationContext = createContext<HeaderPresentation \| null>/);
  assertSourceMatch(navigation, /const HeaderPresentationDispatchContext = createContext<SetHeaderPresentation \| null>/);
  assertSourceMatch(navigation, /const NavigationMenuContext = createContext<NavigationMenuContextValue \| null>/);
  assertSourceMatch(navigation, /<HeaderPresentationProvider>\{children\}<\/HeaderPresentationProvider>[\s\S]*<AppSidebar \/>/);
  assertSourceDoesNotMatch(navigation, /type NavigationContextValue/);
  assertSourceDoesNotMatch(navigation, /useAppNavigation/);
});

test("compact header identities appear only after twelve scroll points", async () => {
  const threshold = await source("src/components/navigation/header-scroll.ts");
  assertSourceMatch(threshold, /HEADER_IDENTITY_SCROLL_THRESHOLD = 12/);
  assertSourceMatch(threshold, /return offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD/);
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
    assertSourceMatch(screen, /useHeaderPresentation/);
    assertSourceMatch(screen, /<Screen[\s\S]*headerMode="preserve"/);
  }

  const compositionPicker = await source("src/components/pickers/composition-picker-screen.tsx");
  assertSourceMatch(compositionPicker, /useHeaderPresentation/);
  assertSourceMatch(compositionPicker, /setHeaderPresentation\(\{ action: selectedId \? undefined : \{ label: "Cancelar"/);
  assertSourceMatch(compositionPicker, /return \(\) => setHeaderPresentation\(\{ mode: "default" \}\)/);
  assertSourceMatch(compositionPicker, /<SafeAreaView edges=\{\["left", "right"\]\}/);

  const comparator = await source("src/app/comparator/index.tsx");
  assertSourceMatch(comparator, /mode: "back", title: savedId \? "Editar comparación" : "Nueva comparación"/);
  assertSourceMatch(comparator, /setHeaderPresentation\(\{ fallback, mode: "back", title: savedId \? "Editar comparación" : "Nueva comparación" \}\)/);
  assertSourceDoesNotMatch(comparator, /title=\{savedId \? "Editar Comparación" : "Nueva Comparación"\}/);
  assertSourceDoesNotMatch(comparator, /<ComparisonKindTabs kind=\{kind\}/);
  assertSourceMatch(comparator, /scrollHeader=\{<SectionPageHeader countLabel="comparaciones" section="comparator" subtitle="Compara los elementos de tu librería\. Comprende las similitudes y diferencias, y reemplázalos en tu dieta\." title="Comparaciones" \/>\}/);
  assertSourceMatch(comparator, /stickyHeader=\{<ComparisonKindTabs counts=\{counts\}/);
  assertSourceMatch(comparator, /stickyHeaderStyle=\{styles\.dashboardStickyHeader\}/);
  assertSourceMatch(comparator, /<DistributedTabBar<ComparisonKind>/);
  assertSourceMatch(comparator, /identityVisible: compactHeaderVisible[\s\S]*title: "Comparaciones"/);
  assertSourceMatch(comparator, /dashboardStickyHeader: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceDoesNotMatch(comparator, /builderTabs:/);
  assertSourceMatch(comparator, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assertSourceMatch(comparator, /pathname: "\/comparator\/saved\/\[id\]", params: \{ id: String\(saved\.saved_comparison_id\), kind: saved\.kind \}/);
  assertSourceDoesNotMatch(comparator, /<SectionPageHeader count=\{page\?\.total\}/);

  const assistant = await source("src/app/assistant/index.tsx");
  assertSourceMatch(assistant, /action: \{ icon: "more", label: activeSection === "chats" \? "Acciones de Chats" : "Acciones de Propuestas"/);
  assertSourceMatch(assistant, /createAction: \{ icon: "plus", label: "Nuevo chat"/);
  assertSourceDoesNotMatch(assistant, /ProposalFilter|status=\$\{filter\}|Filtro:/);
  assertSourceMatch(assistant, /<AssistantSectionTabs activeSection=\{activeSection\} counts=\{counts\} onChange=\{changeSection\} \/>/);
  assertSourceMatch(assistant, /<AssistantListActions/);
  assertSourceMatch(assistant, /scrollHeader=\{scrollHeader\}/);
  assertSourceMatch(assistant, /stickyHeader=\{mode === "list" \? <AssistantSectionTabs/);
  assertSourceMatch(assistant, /const scrollHeader = \([\s\S]*<CreditDashboardGrid/);
  assertSourceDoesNotMatch(assistant, /const stickyHeader = \([\s\S]*<CreditDashboardGrid/);
  assertSourceMatch(assistant, /stickyHeaderStyle=\{styles\.stickyHeader\}/);
  assertSourceMatch(assistant, /identityVisible: compactHeaderVisible/);
  assertSourceMatch(assistant, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assertSourceMatch(assistant, /const scrollHeader = \([\s\S]*<SectionPageHeader countLabel="elementos" section="chat" title="Asistente Nutricional" \/>/);
  assertSourceMatch(assistant, /stickyHeader: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceDoesNotMatch(assistant, /<SectionPageHeader count=/);
  assertSourceDoesNotMatch(assistant, /disabled: !page\.availability\.is_available/);
  assertSourceDoesNotMatch(assistant, /<Button[^>]*label="Nuevo chat"/);
  const proposalListCard = await source("src/components/proposals/proposal-list-card.tsx");
  assertSourceMatch(proposalListCard, /dailyplan: tokens\.color\.dailyPlan/);
  assertSourceMatch(proposalListCard, /meal: tokens\.color\.meal/);
  assertSourceMatch(proposalListCard, /program: tokens\.color\.program/);
  assertSourceMatch(proposalListCard, /<Card accent=\{proposalEntityColors\[proposal\.attachment_kind\]\} style=\{styles\.proposalCard\}>/);
  assertSourceMatch(proposalListCard, /<EntityCardActions>[\s\S]*<ChevronRight/);

  const inbox = await source("src/app/inbox.tsx");
  assertSourceMatch(inbox, /setHeaderPresentation\(\{ identityVisible: compactHeaderVisible, mode: "default", title: "Compartidos" \}\)/);
  assertSourceMatch(inbox, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);

  const libraryList = await source("src/components/libraries/library-list-screen.tsx");
  assertSourceMatch(libraryList, /mode: "library-list"[\s\S]*identityVisible: compactHeaderVisible/);
  assertSourceMatch(libraryList, /isHeaderIdentityVisible\(nativeEvent\.contentOffset\.y\)/);

  const navigation = await source("src/components/navigation/app-navigation.tsx");
  assertSourceMatch(navigation, /\(headerPresentation\.action\?\.icon === "more" \|\| headerPresentation\.action\?\.icon === "plus"\) && styles\.backHeaderIconAction/);
  assertSourceMatch(navigation, /backHeaderIconAction: \{ paddingHorizontal: 0, width: 44 \}/);

  const libraryDetail = await source("src/components/libraries/library-detail-screen.tsx");
  assertSourceMatch(libraryDetail, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assertSourceDoesNotMatch(libraryDetail, /subtitle: "Mis librerías"/);
  assertSourceMatch(libraryDetail, /<ProgramDetailPreview[\s\S]*onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);

  const calendarizedDay = await source("src/app/program/days/[id].tsx");
  assertSourceMatch(calendarizedDay, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assertSourceDoesNotMatch(calendarizedDay, /subtitle: "Mi programa activo"/);

  const calendarizedMeal = await source("src/app/program/days/[id]/meals/[mealKey].tsx");
  assertSourceMatch(calendarizedMeal, /mode: "library-detail"[\s\S]*identityVisible: compactHeaderVisible/);
  assertSourceDoesNotMatch(calendarizedMeal, /subtitle: "Mi programa activo"/);

  const proposals = await source("src/app/proposals/index.tsx");
  assertSourceMatch(proposals, /<Redirect href=\{\{ pathname: "\/assistant", params: \{ section: "proposals" \} \}\} \/>/);

  const proposalDetail = await source("src/app/proposals/[id].tsx");
  assertSourceMatch(proposalDetail, /fallback: "\/assistant\?section=proposals" as Href, mode: "back", title: "Detalle de propuesta"/);
  assertSourceMatch(proposalDetail, /<Screen headerMode="preserve">/);

  const creditDashboard = await source("src/components/assistant/credit-dashboard-grid.tsx");
  assertSourceMatch(creditDashboard, /planName\?: string/);
  assertSourceMatch(creditDashboard, /onPress\?: \(\) => void/);
  assertSourceMatch(creditDashboard, /\{onPress \? <View style=\{\[styles\.column, styles\.actionColumn\]\}>/);
  assertSourceMatch(assistant, /scrollHeader: \{ alignSelf: "stretch", gap: tokens\.spacing\.md \}/);
  assertSourceMatch(assistant, /<CreditDashboardGrid[\s\S]*availableCredits=\{chatPage\.availability\.available_credits\}[\s\S]*bleed[\s\S]*onPress=\{\(\) => router\.push\("\/subscription" as Href\)\}[\s\S]*planName=\{planName \?\? undefined\}/);

  const tabs = await source("src/components/assistant/assistant-section-tabs.tsx");
  assertSourceMatch(tabs, /MessageCircle/);
  assertSourceMatch(tabs, /ClipboardCheck/);
  assertSourceMatch(tabs, /DistributedTabBar<AssistantSection>/);
  assertSourceMatch(tabs, /count: counts\.chats/);
  assertSourceMatch(tabs, /count: counts\.proposals/);
  assertSourceDoesNotMatch(tabs, /PanelTabs/);
  assertSourceDoesNotMatch(tabs, /StyleSheet\.create/);
  assertSourceDoesNotMatch(tabs, /useRouter|router\.replace|href:/);

  const actions = await source("src/components/assistant/assistant-list-actions.tsx");
  assertSourceMatch(actions, /label="Editar lista"/);
  assertSourceDoesNotMatch(actions, /label="Nuevo chat"/);
  for (const label of ["Ver todas", "Ver pendientes", "Ver aprobadas", "Ver aplicadas", "Ver rechazadas"]) {
    assertSourceDoesNotMatch(actions, new RegExp(label));
  }
});
