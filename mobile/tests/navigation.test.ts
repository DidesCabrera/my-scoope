import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { listAvailableProductAreas, productAreas } from "../src/navigation/product-areas";
import { assertSourceDoesNotMatch, assertSourceMatch } from "./support/source-contract";

async function readSources(...relativePaths: string[]) {
  return Promise.all(relativePaths.map((relativePath) => readFile(path.resolve(process.cwd(), relativePath), "utf8")));
}

test("the consumer navigation catalog includes every MCE product area", () => {
  assert.deepEqual(productAreas.map((area) => area.key), [
    "home",
    "program",
    "comparator",
    "inbox",
    "assistant",
  ]);
});

test("only product areas with a functional route are exposed in the sidebar", () => {
  const available = listAvailableProductAreas();
  assert.deepEqual(available.map((area) => area.key), ["home", "program", "comparator", "inbox", "assistant"]);
  assert.deepEqual(available.map((area) => area.label), ["Inicio", "Mi programa activo", "Comparaciones", "Compartidos", "Asistente Nutricional"]);
  assert.ok(available.every((area) => String(area.href).startsWith("/")));
});

test("MCE07 product journeys have native destinations and refocus refreshes", async () => {
  const proposal = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id].tsx"), "utf8");
  const proposalEntity = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id]/entity.tsx"), "utf8");
  const comparison = await readFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  const comparisonList = await readFile(path.resolve(process.cwd(), "src/components/comparisons/saved-comparison-list-card.tsx"), "utf8");
  const comparisonActions = await readFile(path.resolve(process.cwd(), "src/components/comparisons/saved-comparison-actions.tsx"), "utf8");
  const program = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  const programDay = await readFile(path.resolve(process.cwd(), "src/app/program/days/[id].tsx"), "utf8");
  const programMeal = await readFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");
  const today = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  const account = await readFile(path.resolve(process.cwd(), "src/app/account.tsx"), "utf8");
  assertSourceMatch(proposal, /\/proposals\/\$\{proposal\.id\}\/entity/);
  assertSourceMatch(proposalEntity, /\/libraries\/meals\//);
  assertSourceMatch(proposalEntity, /\/libraries\/daily-plans\//);
  assertSourceMatch(proposalEntity, /\/proposals\/\$\{proposal\.id\}\/entity\/meals\//);
  assertSourceDoesNotMatch(comparison, /Usar en el Asistente|Volver a guardadas/);
  assertSourceDoesNotMatch(comparison, /forceFallback: true/);
  assertSourceMatch(comparison, /params: \{ kind \}/);
  assertSourceMatch(comparison, /<Screen[\s\S]*headerMode="preserve"[\s\S]*scrollHeader=\{<AppHeader/);
  assertSourceMatch(comparison, /eyebrowIcon=\{<EntityIcon entity=\{entity\} size="compact" \/>\}/);
  assertSourceMatch(comparison, /kind === "dailyplans" \? "dailyPlan" : kind === "meals" \? "meal" : "food"/);
  assertSourceMatch(comparisonList, /<EntityIcon entity=\{entity\} size="compact" \/>[\s\S]*Comparación \{item\.kind_label\}/);
  assertSourceMatch(comparisonList, /<SavedComparisonPreviewPanels items=\{item\.items\} scope=\{entity\} \/>/);
  assertSourceMatch(comparisonList, /<SavedComparisonPreviewPanels items=\{item\.items\} scope=\{entity\} \/>[\s\S]*<EntityCardActions>[\s\S]*<EntityCardAction[\s\S]*<ChevronRight color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(comparisonList, /<Card accent=\{entityColor\} style=\{styles\.savedCard\}>/);
  assertSourceMatch(comparisonList, /savedCard: \{ paddingBottom: tokens\.card\.innerPadding \}/);
  assertSourceMatch(comparisonList, /backgroundColor=\{`\$\{entityColor\}1A`\}[\s\S]*borderColor=\{entityColor\}[\s\S]*label=\{comparisonCountLabel\(item\.kind, item\.item_count\)\}[\s\S]*textColor=\{tokens\.color\.entityIconForeground\}/);
  assertSourceMatch(comparisonList, /foods: \{ plural: "Alimentos", singular: "Alimento" \}[\s\S]*meals: \{ plural: "Comidas", singular: "Comida" \}[\s\S]*dailyplans: \{ plural: "Planes diarios", singular: "Plan diario" \}/);
  assertSourceDoesNotMatch(comparisonList, /Ver comparación guardada/);
  assertSourceDoesNotMatch(comparisonList, /DateTimeFormat|item\.updated_at/);
  assertSourceMatch(comparisonList, /savedChip: \{[^}]*marginTop: tokens\.spacing\.xs/);
  assertSourceMatch(comparison, /method: "PATCH"/);
  assertSourceMatch(comparisonActions, /Editar nombre/);
  assertSourceMatch(comparisonActions, /Guardar nombre/);
  assertSourceDoesNotMatch(program, /Abrir plan de hoy/);
  assertSourceMatch(program, /CalendarizedProgramPlanning/);
  assertSourceMatch(programDay, /<EntityDetailPage/);
  assertSourceMatch(programDay, /title="Tabla de comparación entre comidas"/);
  assertSourceMatch(programDay, /title="Detalle de cada Comida"/);
  assertSourceMatch(programDay, /<NutritionEntityCard/);
  assertSourceMatch(programDay, /\/program\/days\/\[id\]\/meals\/\[mealKey\]/);
  assertSourceMatch(programDay, /<ChevronRight/);
  assertSourceMatch(programDay, /mode: "library-detail",[\s\S]*entity: "dailyPlan"/);
  assertSourceMatch(programMeal, /mode: "library-detail"/);
  assertSourceMatch(programMeal, /entity: "meal"/);
  assertSourceMatch(today, /\/program/);
  assertSourceMatch(today, /\/api\/v1\/days\/\$\{todayDayId\}\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/check-ins/);
  assertSourceMatch(today, /\/api\/v1\/today\/pinned-plan\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/check-ins/);
  assertSourceDoesNotMatch(today, /Mi suscripción|Cuenta, privacidad y ayuda|Configurar recordatorios/);
  assertSourceMatch(account, /label="Mejorar mi suscripción"[\s\S]*variant="multicolor"/);
  assertSourceMatch(account, /<AppHeader eyebrow="Mi cuenta" eyebrowIcon=\{<SectionIcon color=\{tokens\.color\.textSoft\} section="profile" \/>\}/);
  assertSourceDoesNotMatch(account, /eyebrow="Tu cuenta"/);
  assertSourceMatch(account, /router\.push\("\/subscription" as Href\)/);
  assertSourceMatch(account, /apiRequest<EntitlementsData>\("\/api\/v1\/entitlements"\)/);
  assertSourceMatch(account, /entitlements\?\.plan_name/);
  assertSourceMatch(account, /<Card accent=\{subscriptionPlanAccent\(entitlements\?\.plan_name\)\}>/);
  assertSourceMatch(account, /<AssistantCreditBalance availability=\{entitlements\} contained \/>/);
  assertSourceDoesNotMatch(account, /subscriptionIcon|plan actual/);
  assertSourceMatch(account, /<ProposalReviewSection eyebrow="INFORMACIÓN DE LA CUENTA">/);
  assertSourceMatch(account, /label: "Nombre de usuario"/);
  assertSourceMatch(account, /label: "Correo electrónico"/);
  assertSourceMatch(account, /label: "Fecha de ingreso"/);
  assertSourceMatch(account, /<AccountInformationRows items=/);
  assertSourceMatch(account, /informationValue: \{[^}]*textAlign: "right"/);
  assertSourceDoesNotMatch(account, /<ProposalMetricGrid/);
  assertSourceDoesNotMatch(account, /<Card accent=\{tokens\.color\.interactivePrimary\}>/);
  assertSourceMatch(account, /label="Cerrar sesión"/);
  assertSourceMatch(account, /signOutSpacing: \{ marginTop: 26 \}/);
  assertSourceMatch(account, /icon=\{<LogOut color=\{tokens\.color\.textMain\} size=\{18\} \/>\} label="Cerrar sesión"/);
  assertSourceMatch(account, /signOut\(\)\.then\(\(\) => router\.replace\("\/login"\)\)/);
  assertSourceDoesNotMatch(account, /<SectionTitle title="Sesión"/);
  assertSourceDoesNotMatch(account, /Cierra tu sesión en este dispositivo/);
  assertSourceMatch(account, /eyebrow="INFORMACIÓN DE LA CUENTA">[\s\S]*<\/ProposalReviewSection>[\s\S]*My Scoope no reemplaza atención médica[\s\S]*label="Cerrar sesión"/);
  assertSourceMatch(account, /label: "Acciones de mi cuenta"/);
  assertSourceMatch(account, /accountActions === "menu"/);
  assertSourceMatch(account, /label="Editar nombre de usuario"/);
  assertSourceMatch(account, /<ActionSheetHeader onClose=\{closeAccountActions\} section="profile"/);
  assertSourceMatch(account, /\/api\/v1\/account\/username/);
  assertSourceMatch(account, /method: "PATCH"/);
  assertSourceMatch(account, /label="Guardar nombre"/);
  assertSourceMatch(account, /setAccountActions\("delete"\)/);
  assertSourceMatch(account, /accountActions === "delete" \? \(/);
  assertSourceMatch(account, /onDismiss=\{finishClosingAccountActions\}/);
  assertSourceMatch(account, /visible=\{accountActionsVisible\}/);
  assertSourceMatch(account, /<ActionSheetModal/);
  assertSourceDoesNotMatch(account, /Política de privacidad|Términos de uso|Cancelaciones y reembolsos/);
  assertSourceMatch(account, /<ActionSheetAction icon=\{LifeBuoy\} label="Centro de soporte"/);
  assertSourceMatch(account, /<ActionSheetAction destructive icon=\{Trash2\} label="Eliminar cuenta"/);
  assertSourceDoesNotMatch(account, /<Card accent=\{tokens\.color\.danger\}>/);
  assertSourceDoesNotMatch(account, /<SectionTitle title="Privacidad y ayuda"/);
  assertSourceDoesNotMatch(account, /label="Volver a hoy"/);
  for (const screen of [proposal, proposalEntity, comparison, program, programDay, programMeal, today]) assertSourceMatch(screen, /useFocusEffect/);
});

test("the native sidebar keeps sign-out inside the account screen", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  assertSourceMatch(navigation, /headerPresentation\.action\?\.icon === "more" && styles\.backHeaderMenuAction/);
  assertSourceMatch(navigation, /backHeaderMenuAction: \{ alignItems: "flex-end", paddingHorizontal: 0, paddingRight: tokens\.spacing\.sm, width: 92 \}/);
  assertSourceMatch(navigation, /inbox: UserPlus/);
  assertSourceDoesNotMatch(navigation, /accessibilityLabel="Cerrar sesión"|signOutButton|drawerFooter/);
});

test("the native sidebar uses the app surface without section separators", async () => {
  const [navigation, sidebarItems] = await readSources(
    "src/components/navigation/app-navigation.tsx",
    "src/components/navigation/sidebar-items.tsx",
  );

  assertSourceMatch(navigation, /drawer: \{ backgroundColor: tokens\.color\.surfaceApp/);
  assertSourceMatch(navigation, /drawerHeader: \{[^}]*paddingHorizontal: tokens\.spacing\.md \* 2/);
  assertSourceMatch(navigation, /accessibilityLabel="Cerrar menú"[\s\S]*?<PanelRight color=\{tokens\.color\.textMuted\} size=\{24\} strokeWidth=\{2\}/);
  assertSourceDoesNotMatch(navigation, /drawerHeader: \{[^}]*borderBottomWidth/);
  assertSourceDoesNotMatch(navigation, /menuSection: \{[^}]*borderTopWidth/);
  assertSourceMatch(navigation, /menuSectionLabel: \{[^}]*fontSize: tokens\.type\.caption/);
  assertSourceMatch(navigation, /drawerContent: \{ gap: 0/);
  assertSourceMatch(navigation, /<ModalBackdrop accessibilityLabel="Cerrar menú" onPress=\{closeMenu\} \/>/);
  assertSourceDoesNotMatch(navigation, /scrim: \{ backgroundColor: "rgba\(0,0,0,0\.72\)"/);
  assertSourceMatch(navigation, /menuSection: \{ gap: 0/);
  assertSourceMatch(sidebarItems, /label: \{ color: tokens\.color\.textMain[^}]*fontSize: tokens\.type\.body/);
  assertSourceMatch(sidebarItems, /<Icon color=\{assistant \? tokens\.color\.surfaceApp : tokens\.color\.textMain\}/);
  assertSourceDoesNotMatch(sidebarItems, /active \? tokens\.color\.textMain : tokens\.color\.textMuted/);
  assertSourceMatch(sidebarItems, /countChip: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*minWidth: 30[^}]*paddingVertical: tokens\.spacing\.xs/);
  assertSourceDoesNotMatch(sidebarItems, /singleDigitCount|countChipSingle/);
  assertSourceMatch(navigation, /apiRequest<HomeData>\("\/api\/v1\/home"\)/);
  assertSourceMatch(navigation, /entity === "dailyPlan" \? counts\.daily_plan : counts\[entity\]/);
  assertSourceMatch(navigation, /<EntitySidebarEntry count=\{libraryCount\(libraryCounts, item\.entity\)\}/);
  assertSourceMatch(sidebarItems, /item: \{[^}]*minHeight: 48/);
  assertSourceMatch(navigation, /<ScrollView[^>]*style=\{styles\.drawerScroll\}[\s\S]*<View style=\{\[styles\.creditDashboardShadow, \{ width: drawerWidth - tokens\.spacing\.md \}\]\}>/);
  assertSourceMatch(navigation, /LinearGradient id="sidebar-credit-macros"[\s\S]*tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat/);
  assertSourceMatch(navigation, /creditDashboardShadow: \{[\s\S]*?elevation: 5[\s\S]*?shadowOpacity: 0\.24/);
  assertSourceMatch(navigation, /width: drawerWidth - tokens\.spacing\.md/);
  assertSourceMatch(navigation, /creditDashboardShadow: \{[^}]*marginHorizontal: tokens\.spacing\.md/);
  assertSourceMatch(navigation, /creditDashboardEyebrow}>Plan<[\s\S]*creditDashboardPlanTitle}>\{creditSummary\.planName\}[\s\S]*creditDashboardCreditValue}>\{creditSummary\.availableCredits\}[\s\S]*creditDashboardAvailableLabel}>créditos disponibles/);
  assertSourceMatch(navigation, /creditDashboardCredits: \{[^}]*alignItems: "flex-end"/);
  assertSourceMatch(navigation, /creditDashboardPlan: \{[^}]*gap: 0[^}]*paddingLeft: tokens\.spacing\.xs/);
  assertSourceDoesNotMatch(navigation, /creditDashboardPlan: \{[^}]*paddingBottom/);
  assertSourceMatch(navigation, /creditDashboard: \{[^}]*minHeight: 58/);
  assertSourceMatch(navigation, /creditDashboardCreditValue: \{[^}]*fontSize: 15/);
  assertSourceMatch(navigation, /creditDashboardPlanTitle: \{[^}]*fontSize: 24/);
  assertSourceMatch(navigation, /creditDashboardAction: \{[^}]*marginRight: tokens\.spacing\.md/);
  assertSourceMatch(navigation, /<Pressable accessibilityLabel="Abrir Suscripciones y bolsas"[\s\S]*onPress=\{openCredits\}[\s\S]*<ChevronRight/);
  assertSourceMatch(navigation, /secondaryPrimaryItems[\s\S]*href: "\/personal-records"[\s\S]*label: "Fichas personales"[\s\S]*href: "\/system-foundations"[\s\S]*label: "Fundamentos Sistema"/);
  assertSourceMatch(navigation, /item\.href === "\/inbox"[\s\S]*secondaryPrimaryItems\.map/);
  assertSourceDoesNotMatch(navigation, /href: "\/account"[^\n]*[\s\S]{0,250}href: "\/personal-records"/);
});

test("personal records groups the persisted nutrition inputs", async () => {
  const records = await readFile(path.resolve(process.cwd(), "src/app/personal-records.tsx"), "utf8");

  assertSourceMatch(records, /"\/api\/v1\/onboarding\/state"/);
  assertSourceMatch(records, /title: "Ficha corporal"/);
  assertSourceMatch(records, /title: "Objetivo y actividad"/);
  assertSourceMatch(records, /title: "Preferencias alimentarias"/);
  assertSourceMatch(records, /title: "Métricas corporales"/);
  assertSourceMatch(records, /title: "Métricas corporales"[\s\S]*title: "Ficha corporal"/);
  assertSourceMatch(records, /<Text style=\{styles\.eyebrow\}>FICHA PERSONAL<\/Text>/);
  assertSourceMatch(records, /title: \{[^}]*fontSize: tokens\.type\.section/);
  assertSourceDoesNotMatch(records, /subtitle:/);
  assertSourceDoesNotMatch(records, /Revisar con el Asistente/);
  assertSourceMatch(records, /<Pencil color=\{tokens\.color\.textMuted\}/);
  assertSourceDoesNotMatch(records, /label: "Editar información"/);
  assertSourceMatch(records, /row: \{[^}]*alignItems: "center"[^}]*minHeight: 46[^}]*paddingVertical: tokens\.spacing\.xs/);
  assertSourceMatch(records, /label: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceMatch(records, /value: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceMatch(records, /<View style=\{styles\.headingCopy\}>[\s\S]*<View style=\{styles\.icon\}>/);
  const editor = await readFile(path.resolve(process.cwd(), "src/app/personal-records-edit.tsx"), "utf8");
  assertSourceMatch(editor, /`\/api\/v1\/personal-records\/\$\{section\}`/);
  assertSourceMatch(editor, /method: "PATCH"/);
});

test("system foundations exposes nutrition and product-manual journeys", async () => {
  const [home, catalog, detail] = await readSources(
    "src/app/system-foundations/index.tsx",
    "src/app/system-foundations/[kind]/index.tsx",
    "src/app/system-foundations/[kind]/[slug].tsx",
  );

  assertSourceMatch(home, /Fundamentos Nutricionales/);
  assertSourceMatch(home, /Manuales de uso/);
  assertSourceMatch(home, /<View style=\{learningStyles\.cardText\}>[\s\S]*<LearningIcon name="heart-pulse"/);
  assertSourceMatch(home, /<View style=\{learningStyles\.cardText\}>[\s\S]*<LearningIcon name="book-marked"/);
  assertSourceMatch(home, /<ChevronRight color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(catalog, /"\/api\/v1\/learning"/);
  assertSourceMatch(catalog, /<View style=\{learningStyles\.cardText\}>[\s\S]*<LearningIcon/);
  assertSourceMatch(catalog, /<ChevronRight color=\{tokens\.color\.textMuted\}/);
  assertSourceDoesNotMatch(home, /label="Ver fundamentos"|label="Ver manuales"/);
  assertSourceDoesNotMatch(catalog, /label="Leer detalle"/);
  assertSourceMatch(detail, /Contenido educativo general/);
  assertSourceMatch(detail, /article\.sections\.map/);
  assertSourceMatch(detail, /<Screen contentStyle=\{styles\.content\}/);
  assertSourceMatch(detail, /content: \{ gap: tokens\.spacing\.md \}/);
  assertSourceMatch(detail, /transparentCard: \{ backgroundColor: "transparent", marginHorizontal: 0, paddingHorizontal: 0, paddingVertical: 0 \}/);
  assertSourceMatch(detail, /<LearningIcon name=\{article\.icon\} \/>[\s\S]*<AppHeader eyebrow=/);
  assertSourceMatch(detail, /<Card style=\{\[styles\.intro, styles\.transparentCard\]\}><Text/);
  assertSourceMatch(detail, /<Card key=\{section\.heading\} style=\{\[styles\.section, styles\.transparentCard\]\}/);
});

test("shared screens use compact scroll identities and only Home keeps the centered logo", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const entityIdentity = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-entity-identity.tsx"), "utf8");
  const headerScroll = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-scroll.ts"), "utf8");
  const libraryList = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const screenLayout = await readFile(path.resolve(process.cwd(), "src/components/ui/layout.tsx"), "utf8");
  const headerBody = navigation.slice(navigation.indexOf("export function AppNavigationHeader"), navigation.indexOf("export function useHeaderPresentation"));
  assertSourceMatch(headerBody, /isHome \? <View pointerEvents="none" style=\{styles\.headerLogo\}><MyScoopeBrandLogo compact \/>/);
  assertSourceMatch(headerBody, /HeaderIdentity/);
  assertSourceMatch(headerBody, /defaultIdentityVisible/);
  assertSourceMatch(navigation, /Icon color=\{tokens\.color\.textMain\}/);
  assertSourceMatch(entityIdentity, /<EntityIcon entity=\{entity\} size="header" \/>/);
  assertSourceDoesNotMatch(entityIdentity, /tone="white"/);
  assertSourceMatch(screenLayout, /isHeaderIdentityVisible\([^)]*nativeEvent\.contentOffset\.y\)/);
  assertSourceMatch(headerScroll, /HEADER_IDENTITY_SCROLL_THRESHOLD = 12/);
  assertSourceMatch(headerScroll, /offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD/);
  assertSourceMatch(screenLayout, /identityVisible: compactHeaderVisible/);
  assertSourceMatch(libraryList, /stickyHeaderIndices=\{mode === "list" \? \[1\] : undefined\}/);
  assertSourceDoesNotMatch(libraryList, /searchOffset/);
  assertSourceMatch(libraryList, /stickySearch: \{ backgroundColor: tokens\.color\.surfaceApp, marginHorizontal:/);
  assertSourceDoesNotMatch(libraryList, /stickySearchPinned|searchPinned/);
  assertSourceMatch(navigation, /<Plus color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(navigation, /headerPresentation\.createAction/);
  assertSourceMatch(navigation, /height: 48/);
  assertSourceMatch(navigation, /<Pressable accessibilityLabel="Ir a Inicio"[\s\S]*onPress=\{openHome\}[\s\S]*<MyScoopeBrandLogo compact \/>/);
  const logo = await readFile(path.resolve(process.cwd(), "src/components/ui/my-scoope-logo.tsx"), "utf8");
  assertSourceMatch(logo, /logoText: \{[^}]*fontSize: 18/);
  assertSourceMatch(logo, /logoBar: \{[^}]*height: 3, width: 13/);
  const globalHeaderStyle = navigation.slice(navigation.indexOf("header: { alignItems"), navigation.indexOf("headerButton: {"));
  assertSourceDoesNotMatch(globalHeaderStyle, /borderBottom/);
  assertSourceMatch(navigation, /backHeaderSide: \{ alignItems: "flex-start", paddingLeft: tokens\.spacing\.lg, width: 92 \}/);
});
