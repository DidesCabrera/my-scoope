import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { listAvailableProductAreas, productAreas } from "../src/navigation/product-areas";
import { assertSourceDoesNotMatch, assertSourceMatch } from "./support/source-contract";

test("the consumer navigation catalog includes every MCE product area", () => {
  assert.deepEqual(productAreas.map((area) => area.key), [
    "home",
    "program",
    "assistant",
    "comparator",
    "inbox",
  ]);
});

test("only product areas with a functional route are exposed in the sidebar", () => {
  const available = listAvailableProductAreas();
  assert.deepEqual(available.map((area) => area.key), ["home", "program", "assistant", "comparator", "inbox"]);
  assert.deepEqual(available.map((area) => area.label), ["Inicio", "Mi programa activo", "Asistente Nutricional", "Comparaciones", "Compartidos"]);
  assert.ok(available.every((area) => String(area.href).startsWith("/")));
});

test("MCE07 product journeys have native destinations and refocus refreshes", async () => {
  const proposal = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id].tsx"), "utf8");
  const proposalEntity = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id]/entity.tsx"), "utf8");
  const comparison = await readFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  const comparisonList = await readFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
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
  assertSourceMatch(comparison, /forceFallback: true/);
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
  assertSourceDoesNotMatch(today, /check-in/);
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
  assertSourceMatch(account, /<ActionSheetAction icon=\{ExternalLink\} label="Política de privacidad"/);
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
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const sidebarItems = await readFile(path.resolve(process.cwd(), "src/components/navigation/sidebar-items.tsx"), "utf8");

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
  assertSourceMatch(sidebarItems, /label: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceMatch(sidebarItems, /item: \{[^}]*minHeight: 48/);
});

test("shared screens use compact scroll identities and only Home keeps the centered logo", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const entityIdentity = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-entity-identity.tsx"), "utf8");
  const headerScroll = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-scroll.ts"), "utf8");
  const libraryList = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const screenLayout = await readFile(path.resolve(process.cwd(), "src/components/ui/layout.tsx"), "utf8");
  const headerBody = navigation.slice(navigation.indexOf("export function AppNavigationHeader"), navigation.indexOf("export function useHeaderPresentation"));
  assertSourceMatch(headerBody, /isHome \? <View pointerEvents="none" style=\{styles\.headerLogo\}><MyScoopeLogo/);
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
  assertSourceMatch(navigation, /<MyScoopeLogo \/>/);
  const logo = await readFile(path.resolve(process.cwd(), "src/components/ui/my-scoope-logo.tsx"), "utf8");
  assertSourceMatch(logo, /logoText: \{[^}]*fontSize: 18/);
  assertSourceMatch(logo, /logoBar: \{[^}]*height: 3, width: 13/);
  const globalHeaderStyle = navigation.slice(navigation.indexOf("header: { alignItems"), navigation.indexOf("headerButton: {"));
  assertSourceDoesNotMatch(globalHeaderStyle, /borderBottom/);
  assertSourceMatch(navigation, /backHeaderSide: \{ alignItems: "flex-start", paddingLeft: tokens\.spacing\.lg, width: 92 \}/);
});
