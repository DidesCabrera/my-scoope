import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { listAvailableProductAreas, productAreas } from "../src/navigation/product-areas";

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
  const program = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  const programDay = await readFile(path.resolve(process.cwd(), "src/app/program/days/[id].tsx"), "utf8");
  const programMeal = await readFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");
  const today = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  const account = await readFile(path.resolve(process.cwd(), "src/app/account.tsx"), "utf8");
  assert.match(proposal, /\/proposals\/\$\{proposal\.id\}\/entity/);
  assert.match(proposalEntity, /\/libraries\/meals\//);
  assert.match(proposalEntity, /\/libraries\/daily-plans\//);
  assert.match(proposalEntity, /\/proposals\/\$\{proposal\.id\}\/entity\/meals\//);
  assert.doesNotMatch(comparison, /Usar en el Asistente|Volver a guardadas/);
  assert.match(comparison, /forceFallback: true/);
  assert.match(comparison, /params: \{ kind \}/);
  assert.match(comparison, /<Screen[\s\S]*headerMode="preserve"[\s\S]*scrollHeader=\{<AppHeader/);
  assert.match(comparison, /eyebrowIcon=\{<EntityIcon entity=\{entity\} size="compact" \/>\}/);
  assert.match(comparison, /kind === "dailyplans" \? "dailyPlan" : kind === "meals" \? "meal" : "food"/);
  assert.doesNotMatch(program, /Abrir plan de hoy/);
  assert.match(program, /CalendarizedProgramPlanning/);
  assert.match(programDay, /<EntityDetailPage/);
  assert.match(programDay, /title="Tabla de comparación entre comidas"/);
  assert.match(programDay, /title="Detalle de cada Comida"/);
  assert.match(programDay, /<NutritionEntityCard/);
  assert.match(programDay, /\/program\/days\/\[id\]\/meals\/\[mealKey\]/);
  assert.match(programDay, /<ChevronRight/);
  assert.match(programDay, /mode: "library-detail",[\s\S]*entity: "dailyPlan"/);
  assert.match(programMeal, /mode: "library-detail"/);
  assert.match(programMeal, /entity: "meal"/);
  assert.match(today, /\/program/);
  assert.doesNotMatch(today, /check-in/);
  assert.doesNotMatch(today, /Mi suscripción|Cuenta, privacidad y ayuda|Configurar recordatorios/);
  assert.match(account, /label="Mi suscripción"/);
  assert.match(account, /router\.push\("\/subscription" as Href\)/);
  assert.match(account, /label="Cerrar sesión"/);
  assert.match(account, /signOut\(\)\.then\(\(\) => router\.replace\("\/login"\)\)/);
  for (const screen of [proposal, proposalEntity, comparison, program, programDay, programMeal, today]) assert.match(screen, /useFocusEffect/);
});

test("the native sidebar keeps sign-out inside the account screen", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  assert.match(navigation, /inbox: UserPlus/);
  assert.doesNotMatch(navigation, /accessibilityLabel="Cerrar sesión"|signOutButton|drawerFooter/);
});

test("the native sidebar uses the app surface without section separators", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const sidebarItems = await readFile(path.resolve(process.cwd(), "src/components/navigation/sidebar-items.tsx"), "utf8");

  assert.match(navigation, /drawer: \{ backgroundColor: tokens\.color\.surfaceApp/);
  assert.match(navigation, /drawerHeader: \{[^}]*paddingHorizontal: tokens\.spacing\.md \* 2/);
  assert.match(navigation, /accessibilityLabel="Cerrar menú"[\s\S]*?<PanelRight color=\{tokens\.color\.textMuted\} size=\{24\} strokeWidth=\{2\}/);
  assert.doesNotMatch(navigation, /drawerHeader: \{[^}]*borderBottomWidth/);
  assert.doesNotMatch(navigation, /menuSection: \{[^}]*borderTopWidth/);
  assert.match(navigation, /menuSectionLabel: \{[^}]*fontSize: tokens\.type\.caption/);
  assert.match(navigation, /drawerContent: \{ gap: 0/);
  assert.match(navigation, /menuSection: \{ gap: 0/);
  assert.match(sidebarItems, /label: \{[^}]*fontSize: tokens\.type\.body/);
  assert.match(sidebarItems, /item: \{[^}]*minHeight: 48/);
});

test("shared screens use compact scroll identities and only Home keeps the centered logo", async () => {
  const navigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  const entityIdentity = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-entity-identity.tsx"), "utf8");
  const headerScroll = await readFile(path.resolve(process.cwd(), "src/components/navigation/header-scroll.ts"), "utf8");
  const libraryList = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");
  const screenLayout = await readFile(path.resolve(process.cwd(), "src/components/ui/layout.tsx"), "utf8");
  const headerBody = navigation.slice(navigation.indexOf("export function AppNavigationHeader"), navigation.indexOf("export function useHeaderPresentation"));
  assert.match(headerBody, /isHome \? <View pointerEvents="none" style=\{styles\.headerLogo\}><MyScoopeLogo/);
  assert.match(headerBody, /HeaderIdentity/);
  assert.match(headerBody, /defaultIdentityVisible/);
  assert.match(navigation, /Icon color=\{tokens\.color\.textMain\}/);
  assert.match(entityIdentity, /<EntityIcon entity=\{entity\} size="header" \/>/);
  assert.doesNotMatch(entityIdentity, /tone="white"/);
  assert.match(screenLayout, /isHeaderIdentityVisible\([^)]*nativeEvent\.contentOffset\.y\)/);
  assert.match(headerScroll, /HEADER_IDENTITY_SCROLL_THRESHOLD = 12/);
  assert.match(headerScroll, /offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD/);
  assert.match(screenLayout, /identityVisible: compactHeaderVisible/);
  assert.match(libraryList, /stickyHeaderIndices=\{\[1\]\}/);
  assert.doesNotMatch(libraryList, /searchOffset/);
  assert.match(libraryList, /stickySearch: \{ backgroundColor: tokens\.color\.surfaceApp, marginHorizontal:/);
  assert.doesNotMatch(libraryList, /stickySearchPinned|searchPinned/);
  assert.match(navigation, /<Plus color=\{tokens\.color\.textMuted\}/);
  assert.match(navigation, /headerPresentation\.createAction/);
  assert.match(navigation, /height: 48/);
  assert.match(navigation, /logoText: \{[^}]*fontSize: 18/);
  assert.match(navigation, /logoBar: \{[^}]*height: 3, width: 13/);
  const globalHeaderStyle = navigation.slice(navigation.indexOf("header: { alignItems"), navigation.indexOf("headerButton: {"));
  assert.doesNotMatch(globalHeaderStyle, /borderBottom/);
  assert.match(navigation, /backHeaderSide: \{ alignItems: "flex-start", paddingLeft: tokens\.spacing\.lg, width: 92 \}/);
});
