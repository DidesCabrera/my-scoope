import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { MobileApiError, userFacingError } from "../src/api/errors";
import { tokens } from "../src/generated/ui-tokens";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("mobile visual grammar exposes the reusable card and nutrition tokens", () => {
  assert.equal(tokens.contract, "myscoope.visual-grammar.v2");
  assert.equal(tokens.radius.card, 26);
  assert.equal(tokens.radius.panel, 22);
  assert.equal(tokens.component.eyebrow.fontWeight, "500");
  assert.equal(tokens.component.entityDetail.kpiMarginTop, 4);
  assert.equal(tokens.color.surfaceApp, "#000000");
  for (const key of ["protein", "carbs", "fat", "kcalSurface", "allocationBarTrack", "allocationPanelTrack", "food", "meal", "dailyPlan", "dpm", "program"] as const) {
    assertSourceMatch(tokens.color[key], /^#[0-9A-F]{6}$/);
  }
  assert.equal(tokens.weight.extraBold, "800");
  assert.equal(tokens.spacing.compact, 6);
  assert.deepEqual(tokens.component.nutritionKpi.regular, {
    totalSize: 96,
    totalBorderWidth: 3,
    totalRadius: 22,
    contentGap: 8,
    barHeight: 24,
    narrowBarHeight: 22,
    barRadius: 6,
  });
  assert.equal(tokens.component.nutritionKpi.nested.totalSize, 76);
  assert.deepEqual(tokens.component.entityHeading, {
    card: { fontSize: 23, lineHeight: 29, indicatorMarginTop: 6, marginTop: 2 },
    pageCompact: { fontSize: 26, lineHeight: 34, marginTop: 2 },
    pageRegular: { fontSize: 28, lineHeight: 36, marginTop: 2 },
  });
});

test("meals embedded in daily plans can be saved back to the library", async () => {
  const mealCards = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"), "utf8");
  const mealDetail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-actions.tsx"), "utf8");
  assertSourceMatch(mealCards, /onSaveToLibrary=\{dailyPlanMealId != null/);
  assertSourceMatch(mealCards, /daily-plans\/\$\{dailyPlanId\}\/meals\/\$\{dailyPlanMealId\}\/save-to-library/);
  assertSourceMatch(mealDetail, /onSaveToLibrary=\{hasMealTimeContext/);
  assertSourceMatch(actions, /label="Guardar en mi biblioteca"/);
});

test("daily plans embedded in programs can be saved back to the library", async () => {
  const planCard = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"), "utf8");
  const programDetail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  assertSourceMatch(planCard, /label: "Guardar en mi biblioteca"/);
  assertSourceMatch(planCard, /onSaveToLibrary/);
  assertSourceMatch(programDetail, /onSaveDailyPlan=\{async \(week, day\)/);
  assertSourceMatch(programDetail, /programs\/\$\{item\.id\}\/weeks\/\$\{week\}\/days\/\$\{day\}\/save-to-library/);
  assertSourceMatch(programDetail, /hasProgramDailyPlanContext/);
});

test("editable text inputs use borderless surfaces throughout the mobile system", async () => {
  const cases: [string, string[]][] = [
    ["src/components/ui/controls.tsx", ["input"]],
    ["src/components/ui/search-field.tsx", ["field"]],
    ["src/components/ui/primitives.tsx", ["input"]],
    ["src/components/comparisons/comparison-components.tsx", ["quantityInput"]],
    ["src/components/pickers/composition-picker-screen.tsx", ["compactFieldInput", "noteInput"]],
    ["src/components/assistant/chat-composer.tsx", ["composer"]],
    ["src/components/calendarization/meal-adherence-check-in.tsx", ["noteInput"]],
  ];

  for (const [relativePath, styles] of cases) {
    const source = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    for (const style of styles) {
      assertSourceDoesNotMatch(source, new RegExp(`${style}: \\{[^}]*border(?:Color|Width)`));
    }
  }
});

test("proposal requirement detail is transparent and has no container padding", async () => {
  const proposalDetail = await readTestFile(
    path.resolve(process.cwd(), "src/components/proposals/proposal-detail.tsx"),
    "utf8",
  );
  assertSourceMatch(proposalDetail, /requestSummary: \{ backgroundColor: "transparent", gap: tokens\.spacing\.md \}/);
  assertSourceDoesNotMatch(proposalDetail, /requestSummary: \{[^}]*padding/);
  assertSourceMatch(proposalDetail, /<SectionHeading title="Requerimiento" \/>/);
  assertSourceDoesNotMatch(proposalDetail, /<SectionHeading title="Detalles de la propuesta" \/>/);
  assertSourceDoesNotMatch(proposalDetail, /<Text style=\{proposalTextStyles\.eyebrow\}>Requerimiento<\/Text>/);
  assertSourceMatch(proposalDetail, /proposedEntity \? <><SectionDivider spacing="compact" \/>\{proposedEntity\}<\/>/);
  assertSourceMatch(proposalDetail, /actions: \{ backgroundColor: "transparent", gap: tokens\.spacing\.sm \}/);
  assertSourceDoesNotMatch(proposalDetail, /actions: \{[^}]*padding/);
});

test("the development UI gallery remains available at /dev/ui-gallery", async () => {
  const gallery = await readTestFile(
    path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"),
    "utf8",
  );
  const storyboardGallery = await readTestFile(
    path.resolve(process.cwd(), "src/components/dev/storyboard-gallery.tsx"),
    "utf8",
  );
  const navigation = await readTestFile(
    path.resolve(process.cwd(), "src/components/dev/gallery-navigation.tsx"),
    "utf8",
  );
  assertSourceMatch(gallery, /export default function UiGalleryScreen/);
  assertSourceMatch(gallery, /if \(!__DEV__\) return <Redirect href="\/" \/>/);
  assertSourceMatch(gallery, /Galería del sistema UI/);
  assertSourceDoesNotMatch(gallery, /<Brand|Referencia interna construida con los componentes reales de la app/);
  assertSourceMatch(gallery, /<OnboardingStoryboardGallery \/>/);
  assertSourceMatch(gallery, /<SubscriptionGallery \/>/);
  assertSourceMatch(gallery, /<DisclosureGallery \/>/);
  assertSourceMatch(navigation, /\{ key: "subscriptions", label: "Suscripciones" \}/);
  assertSourceMatch(navigation, /\{ key: "disclosures", label: "Responsabilidad" \}/);
  const disclosureGallery = await readTestFile(
    path.resolve(process.cwd(), "src/components/dev/disclosure-gallery.tsx"),
    "utf8",
  );
  assert.ok(disclosureGallery.includes("sin aceptación, navegación ni persistencia"));
  assertSourceMatch(disclosureGallery, /Entiendo y quiero continuar/);
  assertSourceMatch(storyboardGallery, /OnboardingJourneyView/);
  assertSourceMatch(storyboardGallery, /step === "plans"[\s\S]*<SubscriptionPreviewContent context="onboarding" topInsetReduction=\{topInsetReductionForOnboardingStoryboard\(step\)\} \/>/);
  assertSourceMatch(storyboardGallery, /Storyboard visual · sin sesión, API ni persistencia/);
  assertSourceMatch(storyboardGallery, /accessibilityLabel="Formatos del onboarding"/);
  assertSourceMatch(storyboardGallery, /tabs=\{previewWidths\.map\(\(preview\) => \(\{ key: preview\.width, label: preview\.label \}\)\)\}/);
  assertSourceMatch(storyboardGallery, /steps\.map\(\(step, index\) =>/);
  assertSourceMatch(storyboardGallery, /String\(index \+ 1\)\.padStart\(2, "0"\).*step\.label/);
  assertSourceDoesNotMatch(storyboardGallery, /accessibilityLabel="Vistas del onboarding"|setOnboardingStep/);
  assertSourceMatch(gallery, /Card-child de programa/);
  assertSourceMatch(gallery, /ProgramChildCard/);
  assertSourceMatch(gallery, /Detalle de programa/);
  assertSourceMatch(gallery, /ProgramDetailPreview/);
  assertSourceMatch(gallery, /ProgramActiveKpis/);
  assertSourceMatch(gallery, /KPI de programa en curso/);
  assertSourceMatch(gallery, /title="Colores de superficies"/);
  for (const surface of ["surfaceApp", "surfacePage", "surfaceCard", "surfaceMuted", "surfaceElevated"]) {
    assertSourceMatch(gallery, new RegExp(surface));
  }

  const nutritionKpi = await readTestFile(
    path.resolve(process.cwd(), "src/components/nutrition/nutrition-kpi-section.tsx"),
    "utf8",
  );
  assertSourceMatch(nutritionKpi, /borderColor: tokens\.color\.kcalBorder/);
  assertSourceMatch(nutritionKpi, /borderRadius: tokens\.component\.nutritionKpi\.regular\.totalRadius/);
  assertSourceMatch(nutritionKpi, /height: tokens\.component\.nutritionKpi\.regular\.totalSize/);
  assertSourceMatch(nutritionKpi, /height: tokens\.component\.nutritionKpi\.nested\.totalSize/);
  assertSourceMatch(nutritionKpi, /variant\?: "nested" \| "regular"/);
  assertSourceMatch(nutritionKpi, /grams: \{[^}]*fontWeight: tokens\.weight\.bold[^}]*letterSpacing: 0/);
  assertSourceMatch(nutritionKpi, /const macroFontSize = width < 420 \? 13 : 14/);
  assertSourceMatch(nutritionKpi, /<ProteinPerKilogramBadge density=\{density\} textSize=\{12\}/);
  assertSourceDoesNotMatch(nutritionKpi, /density\?: "compact" \| "regular"/);
  assertSourceDoesNotMatch(nutritionKpi, /height: compact \? "100%"/);

  const proteinPerKilogramBadge = await readTestFile(
    path.resolve(process.cwd(), "src/components/nutrition/protein-per-kilogram-badge.tsx"),
    "utf8",
  );
  assertSourceMatch(proteinPerKilogramBadge, /text: \{[^}]*fontWeight: tokens\.weight\.bold[^}]*letterSpacing: 0/);

  const allocationBar = await readTestFile(
    path.resolve(process.cwd(), "src/components/nutrition/allocation-bar.tsx"),
    "utf8",
  );
  assertSourceMatch(allocationBar, /panelPercentage: \{[^}]*fontWeight: tokens\.weight\.semibold/);
  assertSourceMatch(allocationBar, /textSize\?: 12 \| 13 \| 14/);

  const libraryCard = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryCard, /NutritionEntityCard.*from "@\/components\/nutrition"/);
  assertSourceMatch(libraryCard, /interactive = true[^}]*navigable = interactive/);
  assertSourceMatch(libraryCard, /navigable \? <EntityCardAction/);
  assertSourceDoesNotMatch(libraryCard, /\.\/nutrition-entity-card/);

  const collectionPageHeader = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/collection-page-header.tsx"),
    "utf8",
  );
  assertSourceMatch(collectionPageHeader, /container: \{ alignItems: "flex-start", gap: tokens\.spacing\.sm/);
  assertSourceMatch(collectionPageHeader, /iconSlot: \{ alignSelf: "flex-start" \}/);
  assertSourceMatch(collectionPageHeader, /function PageHeader[\s\S]*<View style=\{styles\.copy\}>[\s\S]*?<Text style=\{styles\.title\}>\{title\}<\/Text>[\s\S]*\{indicator\}/);
  assertSourceDoesNotMatch(collectionPageHeader, /Bookmark|Mis librerías|eyebrow/);
  assertSourceMatch(collectionPageHeader, /<StructuralIndicators[^\n]*tone="surfaceMuted"/);
  assertSourceMatch(collectionPageHeader, /export function SectionPageHeader/);
  assertSourceMatch(collectionPageHeader, /<SectionIcon section=\{section\} size="hero" \/>/);
  assertSourceMatch(collectionPageHeader, /style=\{styles\.countChip\}/);

  for (const [relativePath, section, title] of [
    ["src/app/comparator/index.tsx", "comparator", "Comparaciones"],
    ["src/app/assistant/index.tsx", "chat", "Asistente Nutricional"],
  ]) {
    const sectionScreen = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assertSourceMatch(sectionScreen, new RegExp(`<SectionPageHeader[^>]*section="${section}"[^>]*title="${title}"`));
    assertSourceDoesNotMatch(sectionScreen, /<AppHeader/);
  }

  const productUiSourceForIndicators = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assertSourceMatch(productUiSourceForIndicators, /chat: Sparkles/);
  assertSourceMatch(productUiSourceForIndicators, /proposal: ClipboardCheck/);
  assertSourceMatch(productUiSourceForIndicators, /comparator: Scale/);
  assertSourceMatch(productUiSourceForIndicators, /tone\?: "identity" \| "surfaceCard" \| "surfaceMuted"/);
  assertSourceMatch(productUiSourceForIndicators, /itemTone === "surfaceMuted" \? tokens\.color\.surfaceMuted : color/);
  assertSourceMatch(productUiSourceForIndicators, /structuralItemSurface: \{ borderColor: tokens\.color\.borderDefault, borderWidth: 1 \}/);

  const typographySource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/typography.tsx"),
    "utf8",
  );
  assertSourceMatch(typographySource, /sectionHeading: \{[^}]*marginBottom: tokens\.spacing\.xs[^}]*marginTop: tokens\.spacing\.sm/);

  const menuPanelSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(menuPanelSource, /menuFoods: \{ color: tokens\.color\.textMain/);
  assertSourceMatch(menuPanelSource, /menuFoods: \{[^}]*lineHeight: 21/);
  assertSourceDoesNotMatch(menuPanelSource, /menuFoods: \{[^}]*opacity:/);

  const libraryEntityPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryEntityPanels, /proteinPerKilogram: item\.protein_per_kilogram/);
  assertSourceMatch(libraryEntityPanels, /eyebrow=\{`Comida \$\{index \+ 1\}`\}/);
  assertSourceDoesNotMatch(libraryEntityPanels, /mealCardMarker|mealCardNumber|mealCardLine/);

  for (const relativePath of [
    "src/app/program/days/[id].tsx",
    "src/components/details/dailyplan-meal-detail-list.tsx",
  ]) {
    const dailyPlanMealCards = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assertSourceMatch(dailyPlanMealCards, /eyebrow=\{`Comida \$\{index \+ 1\}`\}/);
    assertSourceDoesNotMatch(dailyPlanMealCards, /mealCardMarker|mealCardNumber|mealCardLine|markerNumber|markerLine/);
  }
  assertSourceDoesNotMatch(libraryEntityPanels, /protein: \{ grams: item\.protein_grams, allocation: item\.protein_allocation, perKilogram: null \}/);

  const programWeekPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-week-comparison-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(programWeekPanels, /EntityPanelTabs/);
  assertSourceMatch(programWeekPanels, /PanelSurface/);
  assertSourceMatch(programWeekPanels, /MacroCalorieDistribution/);
  assertSourceMatch(programWeekPanels, /PanelAllocationBar/);
  for (const tab of ["Calorías", "Macros", "Dist", "Alloc", "Editar"]) assertSourceMatch(programWeekPanels, new RegExp(tab));
  assertSourceDoesNotMatch(programWeekPanels, /label: "Semanas"/);
  assertSourceMatch(programWeekPanels, /<Pencil/);
  assertSourceMatch(programWeekPanels, /weekName: \{ color: tokens\.color\.textMain/);
  assertSourceMatch(programWeekPanels, /cell: \{[^}]*fontSize: tokens\.type\.caption/);
  assertSourceMatch(programWeekPanels, /row: \{[^}]*minHeight: 48/);
  assertSourceMatch(programWeekPanels, /leadingCell: \{ flexBasis: "38%", flexGrow: 0, flexShrink: 0/);
  assertSourceDoesNotMatch(programWeekPanels, /cell: \{[^}]*fontSize: 11/);
  assertSourceDoesNotMatch(programWeekPanels, /<PanelAllocationBar size="compact"/);
  assertSourceMatch(programWeekPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assertSourceDoesNotMatch(programWeekPanels, /deltaUp|deltaDown|styles\.(?:protein|carbs|fat)(?:[,}\]])/);
  assertSourceMatch(programWeekPanels, /Header columns=\{\[\{ key: "ppk", label: "PpK" \}, \{ key: "protein", label: "Pg", textStyle: styles\.mixedCaseHeaderText \}, \{ key: "carbs", label: "Cg", textStyle: styles\.mixedCaseHeaderText \}, \{ key: "fat", label: "Fg", textStyle: styles\.mixedCaseHeaderText \}\]\}/);
  assertSourceMatch(programWeekPanels, /Header columns=\{\[\{ key: "protein", label: "P%" \}, \{ key: "carbs", label: "C%" \}, \{ key: "fat", label: "F%" \}, \{ key: "protein", label: "P\|C\|F"/);
  assertSourceMatch(programWeekPanels, /SortablePanelHeaderCell/);
  assertSourceMatch(programWeekPanels, /useTemporaryPanelSort/);

  const programDetail = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  assertSourceMatch(programDetail, /ProgramDailyPlanPreview/);
  assertSourceMatch(programDetail, /ProgramDayComparisonPanels/);
  assertSourceMatch(programDetail, /weekData\.foods \?\? \[\]\)\.map\(foodItem\)/);
  assertSourceMatch(programDetail, /: weekFoodItems/);
  assertSourceMatch(programDetail, /useState<number \| null>\(\(\) => filledDays\[0\] \? 0 : null\)/);
  assertSourceMatch(programDetail, /<View style=\{styles\.weekContent\}>/);
  assertSourceDoesNotMatch(programDetail, /<Card(?: muted)? style=\{styles\.weekCard\}>/);
  assertSourceMatch(programDetail, /<ProgramDaySelector/);
  assertSourceMatch(programDetail, /<ProgramWeekTabs/);
  assertSourceMatch(programDetail, /detail=\{`\$\{weeksCount\} \$\{weeksCount === 1 \? "semana" : "semanas"\}`\}/);
  assertSourceMatch(programDetail, /title="Planificación semanal"/);
  assertSourceDoesNotMatch(programDetail, /MajorSectionTitle/);
  assertSourceMatch(programDetail, /<ProgramWeekHeading week=\{week\} \/>/);
  assertSourceMatch(programDetail, /weekContent: \{[^}]*paddingTop: tokens\.spacing\.md/);
  assertSourceDoesNotMatch(programDetail, /weekEyebrow|weekEyebrowText/);
  assertSourceDoesNotMatch(programDetail, /Planificación por semanas/);
  assertSourceDoesNotMatch(programDetail, /planningIdentity|planningTitle/);
  assertSourceMatch(programDetail, /weekContent: \{ gap: tokens\.spacing\.lg, minWidth: 0, paddingTop: tokens\.spacing\.md, width: "100%" \}/);
  assertSourceMatch(programDetail, /<ProgramMetricPreview[^\n]*style=\{layoutStyles\.cardContentBleed\}/);
  assertSourceMatch(programDetail, /<GroupedFoodsCard title=\{`Alimentos semana \$\{week\}`\} items=\{weekData/);
  assertSourceDoesNotMatch(programDetail, /<View style=\{layoutStyles\.cardContentBleed\}><(?:FoodPanels|ProgramDayComparisonPanels|ProgramWeekComparisonPanels)/);
  assertSourceMatch(programDetail, /stickyHeaderIndices=\{\[3\]\}/);
  assertSourceMatch(programDetail, /weekTabsSticky: \{ backgroundColor: tokens\.color\.surfaceApp, marginHorizontal:/);
  assertSourceDoesNotMatch(programDetail, /weekTabsStickyPinned/);
  assertSourceDoesNotMatch(programDetail, /weekTabsOffset|weekTabsPinned/);
  assertSourceMatch(programDetail, /paddingVertical: tokens\.spacing\.sm/);

  const planningControls = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-planning-controls.tsx"),
    "utf8",
  );
  assertSourceMatch(planningControls, /<WeekDaySelectionRing \/>/);
  assertSourceMatch(planningControls, /selected && styles\.dayDateNumberSelected/);
  assertSourceMatch(planningControls, /selected && styles\.dayDateMonthSelected/);
  assertSourceMatch(planningControls, /dayDateMonth: \{[^}]*fontWeight: tokens\.weight\.medium/);
  assertSourceMatch(planningControls, /dayDateMonthSelected: \{ fontWeight: tokens\.weight\.semibold \}/);
  assertSourceMatch(planningControls, /dayDateNumberSelected: \{ fontWeight: tokens\.weight\.bold \}/);
  assertSourceMatch(planningControls, /accessibilityState=\{\{ expanded:/);
  assertSourceMatch(planningControls, /backgroundColor: tokens\.color\.surfaceCard/);
  assertSourceMatch(planningControls, /backgroundColor: tokens\.color\.dailyPlan/);
  assertSourceMatch(planningControls, /<ClipboardList color=\{tokens\.color\.entityIconForeground\} size=\{14\}/);
  assertSourceMatch(planningControls, /<Plus color=\{tokens\.color\.textMain\} size=\{24\} \/>/);
  assertSourceMatch(planningControls, /borderRadius: tokens\.spacing\.compact, height: 24/);
  assertSourceMatch(planningControls, /dayCircle: \{[^}]*borderWidth: 1[^}]*height: 44[^}]*width: 44/);
  assertSourceMatch(planningControls, /dayCircleCompact: \{ height: 40, width: 40 \}/);
  assertSourceMatch(planningControls, /hitSlop=\{compact \? 2 : undefined\}/);
  assertSourceMatch(planningControls, /<ScrollableTabBar[\s\S]*?tabs=\{weeks\.map/);
  assertSourceMatch(planningControls, /export function ProgramWeekHeading/);
  assertSourceMatch(planningControls, /<CalendarRange color=\{tokens\.color\.entityIconForeground\} size=\{11\}/);
  assertSourceMatch(planningControls, /<HeaderMetadataChip kind="date" value=\{detail\} \/>/);
  assertSourceMatch(planningControls, /weekHeadingTitle: \{[^}]*fontSize: tokens\.type\.section[^}]*fontWeight: tokens\.weight\.semibold/);

  const calendarizedPlanning = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedPlanning, /<ProgramWeekHeading detail=\{weekDateRange\(weekDays\)\} week=\{activeWeek\} \/>/);
  assertSourceMatch(calendarizedPlanning, /style=\{styles\.weekContent\}/);
  assertSourceMatch(calendarizedPlanning, /weekContent: \{[^}]*paddingTop: tokens\.spacing\.md/);
  assertSourceDoesNotMatch(calendarizedPlanning, /<Card style=\{styles\.weekCard\}>/);
  assertSourceMatch(calendarizedPlanning, /<ProgramWeekTabs/);
  assertSourceMatch(calendarizedPlanning, /<ProgramDaySelector/);
  assertSourceMatch(calendarizedPlanning, /apiRequest<CalendarizedDayDetail>/);
  assertSourceMatch(calendarizedPlanning, /<CalendarizedDailyPlanCard/);
  assertSourceMatch(calendarizedPlanning, /preferredCalendarizedDay\(days, week, localDate\(\)\)/);
  assertSourceMatch(calendarizedPlanning, /Día sin plan\. No hay un plan diario asignado para esta fecha\./);
  assertSourceMatch(calendarizedPlanning, /isToday: day\.calendar_date === localDate\(\)/);
  assertSourceDoesNotMatch(calendarizedPlanning, /SectionDivider|SectionHeading/);
  assertSourceMatch(calendarizedPlanning, /<ProgramSectionHeader icon=\{Carrot\} subtitle="Revisa las cantidades de alimentos de esta semana; conoce y compara su aporte nutricional real en el programa\." title="Alimentos en esta semana" \/>/);
  assertSourceMatch(calendarizedPlanning, /<GroupedFoodsCard title=\{`Alimentos semana \$\{activeWeek\}`\} items=\{weekFoods\} onOpenItem=/);

  const calendarizedDailyPlanCard = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-daily-plan-card.tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedDailyPlanCard, /<NutritionEntityCard/);
  assertSourceMatch(calendarizedDailyPlanCard, /afterNutrition=\{<DailyMealCompletionCard mealExecution=\{mealExecution\} mealKeys=\{meals\.map\(\(meal\) => meal\.key\)\} \/>\}/);
  assertSourceMatch(calendarizedDailyPlanCard, /<MealPanels/);
  assertSourceMatch(calendarizedDailyPlanCard, /onOpenItem=/);
  assertSourceMatch(calendarizedDailyPlanCard, /pathname: "\/program\/days\/\[id\]\/meals\/\[mealKey\]"/);
  assertSourceMatch(calendarizedDailyPlanCard, /mealKey: meal\.id/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /kpiVariant="nested"/);
  assertSourceMatch(calendarizedDailyPlanCard, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /completedCount: executions\.filter/);
  assertSourceMatch(calendarizedDailyPlanCard, /noteCount: executions\.filter/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /label: "posición"|position\?: \{ dayNumber/);
  assertSourceMatch(calendarizedDailyPlanCard, /eyebrowAccessory=\{<HeaderMetadataChip kind="date" value=\{dateLabel\} \/>\}/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /label: "fecha", tone: "surfaceMuted"/);

  const calendarizedMealDetail = await readTestFile(
    path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedMealDetail, /apiRequest<CalendarizedDayDetail>\(`\/api\/v1\/program\/days\/\$\{dayId\}`\)/);
  assertSourceMatch(calendarizedMealDetail, /day\.plan_snapshot\?\.meals\?\.find/);
  assertSourceMatch(calendarizedMealDetail, /afterNutrition=\{<MealCompletionCard controller=\{adherence\} \/>\}/);
  assertSourceMatch(calendarizedMealDetail, /<FoodPanels\s+editing=\{\{/);
  assertSourceMatch(calendarizedMealDetail, /ordered_keys: items\.map\(\(item\) => item\.id\)/);
  assertSourceMatch(calendarizedMealDetail, /relationKey: food\.id/);
  assertSourceMatch(calendarizedMealDetail, /onEditPortion:/);
  assertSourceMatch(calendarizedMealDetail, /<MealNoteCard controller=\{adherence\} \/>/);
  assertSourceMatch(calendarizedMealDetail, /completion=\{\{/);
  assertSourceMatch(calendarizedMealDetail, /onChange: setExecution/);
  assertSourceMatch(calendarizedMealDetail, /secondaryAction: meal \? \{ icon: "clock", label: "Cambiar hora"/);
  assertSourceMatch(calendarizedMealDetail, /eyebrowAccessory=\{meal\.hour \? <HeaderMetadataChip kind="time" value=\{meal\.hour\.slice\(0, 5\)\} \/> : undefined\}/);
  assertSourceDoesNotMatch(calendarizedMealDetail, /label: "hora", tone: "surfaceCard"/);
  assertSourceMatch(calendarizedMealDetail, /initialAction=\{actionSheet === "change-time" \? "change-time" : undefined\}/);
  assertSourceMatch(calendarizedMealDetail, /timeChangeInMenu=\{false\}/);
  assertSourceDoesNotMatch(calendarizedMealDetail, /\/api\/v1\/library\/meals/);

  const sharedEntityPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(sharedEntityPanels, /accessibilityLabel=\{canOpen \? `Ver detalle de \$\{item\.name\}` : undefined\}/);
  assertSourceMatch(sharedEntityPanels, /<Pressable[\s\S]*style=\{\[styles\.menuRow, index === items\.length - 1 && styles\.rowLast\]\}/);
  assertSourceDoesNotMatch(sharedEntityPanels, /<Pressable[\s\S]*style=\{\(\{ pressed \}\) => \[styles\.menuAction/);
  assertSourceMatch(sharedEntityPanels, /<ChevronRight color=\{tokens\.color\.textMuted\} size=\{19\}/);
  assertSourceMatch(sharedEntityPanels, /menuRow: \{[^}]*gap: tokens\.spacing\.xs[^}]*paddingRight: tokens\.spacing\.xs/);
  assertSourceMatch(sharedEntityPanels, /menuAction: \{[^}]*minWidth: 24/);
  assertSourceMatch(sharedEntityPanels, /<MealRowIdentity completed=\{item\.completed\} menu name=\{item\.name\} projectedLabel=\{item\.projectedLabel\} \/>[\s\S]*item\.time \? \([\s\S]*<Clock color=\{tokens\.color\.textMuted\} size=\{11\} strokeWidth=\{2\} \/>[\s\S]*<Text style=\{styles\.menuTime\}>\{item\.time\}<\/Text>/);
  assertSourceMatch(sharedEntityPanels, /<View style=\{styles\.mealIdentity\}>/);
  assertSourceMatch(sharedEntityPanels, /menuTitleRow: \{ alignItems: "flex-start"/);
  assertSourceMatch(sharedEntityPanels, /menuRow: \{[^}]*paddingBottom: tokens\.spacing\.xl[^}]*paddingTop: tokens\.spacing\.xl/);
  assertSourceMatch(sharedEntityPanels, /menuCopy: \{[^}]*gap: tokens\.spacing\.md/);
  assertSourceMatch(sharedEntityPanels, /menuTimeGroup: \{[^}]*backgroundColor: "transparent"[^}]*borderRadius: tokens\.radius\.pill[^}]*borderWidth: 1[^}]*marginTop: -2[^}]*minHeight: 23[^}]*paddingVertical: 2/);
  assertSourceMatch(sharedEntityPanels, /<MealRowIdentity completed=\{item\.completed\} menu name=\{item\.name\}/);
  assertSourceMatch(sharedEntityPanels, /menuMealName: \{ fontSize: tokens\.type\.caption \+ 1, lineHeight: 19 \}/);
  assertSourceMatch(sharedEntityPanels, /foodItemName: \{ fontWeight: tokens\.weight\.medium \}/);
  assertSourceMatch(sharedEntityPanels, /item\.detailId != null \|\| item\.canOpen/);
  assertSourceMatch(sharedEntityPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assertSourceMatch(libraryEntityPanels, /NutritionAllocationPanel/);
  assertSourceMatch(sharedEntityPanels, /key: "distribution", label: "Dist"/);
  assertSourceMatch(sharedEntityPanels, /<PanelHeaderCell \{\.\.\.sorting\} sortKey="ppk" style=\{styles\.ppkValue\}>PpK<\/PanelHeaderCell>/);
  assertSourceMatch(sharedEntityPanels, /<MacroCalorieDistribution \{\.\.\.item\} style=\{styles\.distributionBar\} \/>/);

  const completionUi = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assertSourceMatch(completionUi, /summarized=\{entity === "dailyPlan"\}/);
  assertSourceMatch(completionUi, /<CheckCheck color=\{tokens\.color\.textMuted\}/);
  assertSourceMatch(completionUi, /<Text style=\{styles\.completionIndicatorCount\}>\{completedCount\}<\/Text>/);
  assertSourceMatch(completionUi, /<Text style=\{styles\.completionIndicatorCount\}>\{noteCount\}<\/Text>/);
  assertSourceMatch(completionUi, /style=\{\[styles\.headingIndicators, page && styles\.headingIndicatorsPage\]\}/);
  assertSourceMatch(completionUi, /headingIndicatorsPage: \{ marginTop: tokens\.spacing\.xs \}/);

  const mealAdherence = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"),
    "utf8",
  );
  assertSourceMatch(mealAdherence, /accessibilityRole="checkbox"/);
  assertSourceMatch(mealAdherence, /onToggle=\{\(nextCompleted\) => void controller\.saveStatus\(nextCompleted\)\}/);
  assertSourceMatch(mealAdherence, /action: "note"/);
  assertSourceMatch(mealAdherence, /Guardar nota/);
  assertSourceMatch(mealAdherence, /Editar nota/);
  assertSourceMatch(mealAdherence, /<Pencil/);
  assertSourceMatch(mealAdherence, /onChange\?\.\(execution\)/);
  assertSourceMatch(mealAdherence, /maxLength=\{500\}/);
  assertSourceMatch(mealAdherence, /action: nextCompleted \? "completed" : "skipped"/);
  assertSourceMatch(mealAdherence, /export function MealCompletionCard/);
  assertSourceMatch(mealAdherence, /export function MealCompletionToggleCard/);
  assertSourceMatch(mealAdherence, /accessibilityLabel="¿Cumpliste con tu comida\?"/);
  assertSourceMatch(mealAdherence, /<CheckCheck color=\{tokens\.color\.textMain\}[^>]*\/>[\s\S]*<Text style=\{styles\.completionLabel\}>¿Cumpliste con tu comida\?/);
  assertSourceMatch(mealAdherence, /onToggle\(!completed\)/);
  assertSourceMatch(mealAdherence, /Haptics\.impactAsync\(Haptics\.ImpactFeedbackStyle\.Rigid\)/);
  assertSourceMatch(mealAdherence, /style=\{styles\.completionRow\}/);
  assertSourceDoesNotMatch(mealAdherence, /saving && styles\.saving|pressed && styles\.pressed[^\n]*completionRow/);
  assertSourceMatch(mealAdherence, /export function MealNoteCard/);
  assertSourceDoesNotMatch(mealAdherence, /Marca la casilla si cumpliste esta comida del programa/);
  assertSourceMatch(mealAdherence, /<MealCompletionSurface>/);
  assertSourceMatch(mealAdherence, /checkbox: \{[^}]*borderRadius: tokens\.radius\.pill/);
  assertSourceMatch(mealAdherence, /completionLabel: \{[^}]*fontSize: 15/);
  assertSourceMatch(mealAdherence, /<SectionDivider spacing="compact" tone="soft" \/>[\s\S]*<SectionHeading title="Nota de esta comida" \/>/);
  assertSourceMatch(mealAdherence, /<SectionHeading title="Nota de esta comida" \/>/);
  assertSourceMatch(mealAdherence, /<SectionHeading title="Nota de esta comida" \/>[\s\S]*<View style=\{styles\.noteSurface\}>/);
  assertSourceDoesNotMatch(mealAdherence, /<ContentPanel/);
  assertSourceMatch(mealAdherence, /controller\.editingNote \? <TextInput[\s\S]*styles\.noteText/);
  assertSourceMatch(mealAdherence, /noteInput: \{[^}]*backgroundColor: tokens\.color\.surfaceMuted/);
  assertSourceMatch(mealAdherence, /noteInput: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceDoesNotMatch(mealAdherence, /noteInput: \{[^}]*borderColor|noteInput: \{[^}]*borderWidth/);
  assertSourceMatch(mealAdherence, /noteSurface: \{[^}]*backgroundColor: "transparent"[^}]*marginTop: tokens\.spacing\.xs/);
  assertSourceMatch(mealAdherence, /noteLabel: \{[^}]*fontSize: tokens\.type\.label - 1[^}]*fontWeight: tokens\.component\.eyebrow\.fontWeight[^}]*textTransform: "uppercase"/);
  assertSourceDoesNotMatch(mealAdherence, /styles\.divider/);

  assertSourceMatch(sharedEntityPanels, /preparationMarkerChecked/);
  assertSourceMatch(sharedEntityPanels, /preparation\.isPrepared\(item\) \? <View style=\{styles\.preparationMarkerChecked\} \/> : null/);
  assertSourceMatch(sharedEntityPanels, /preparationMarker: \{[^}]*borderColor: tokens\.color\.borderDefault/);
  assertSourceMatch(sharedEntityPanels, /preparationMarkerChecked: \{ backgroundColor: tokens\.color\.food, borderRadius: 5, height: 10, width: 10 \}/);
  assertSourceMatch(sharedEntityPanels, /accessibilityRole="checkbox"/);
  assertSourceMatch(sharedEntityPanels, /style=\{\[styles\.preparationValue, styles\.preparationButton\]\}/);
  assertSourceDoesNotMatch(sharedEntityPanels, /styles\.preparationButton, preparation\.disabled && styles\.disabled/);
  assertSourceMatch(sharedEntityPanels, /quantityItemText: \{ fontSize: tokens\.type\.caption \+ 1 \}/);
  assertSourceMatch(sharedEntityPanels, /sortKey="name" style=\{styles\.quantityLeadingCell\}>\{leadingLabel\}<\/PanelHeaderCell>/);
  assertSourceMatch(sharedEntityPanels, /sortKey="quantity" style=\{styles\.quantityValue\}>\{trailingLabel\}<\/PanelHeaderCell>/);
  assertSourceDoesNotMatch(sharedEntityPanels, /quantityHeaderText/);
  assertSourceMatch(sharedEntityPanels, /<PanelItemName item=\{item\} itemNameStyle=\{styles\.quantityItemText\}/);
  assertSourceMatch(sharedEntityPanels, /styles\.quantityValue, styles\.quantityItemText/);
  assertSourceMatch(sharedEntityPanels, /<Text numberOfLines=\{2\} style=\{\[styles\.cell, styles\.editName\]\}>\{item\.name\}<Text style=\{styles\.foodPortionSuffix\}>/);
  assertSourceMatch(sharedEntityPanels, /editIdentity: \{ alignSelf: "stretch", flex: 1, justifyContent: "center", minWidth: 0 \}/);
  assertSourceMatch(sharedEntityPanels, /editName: \{ paddingHorizontal: tokens\.spacing\.xs, textAlign: "left" \}/);
  assertSourceDoesNotMatch(sharedEntityPanels, /editValue: \{[^}]*fontSize/);
  assertSourceMatch(sharedEntityPanels, /row: \{[^}]*minHeight: 44/);
  assertSourceMatch(sharedEntityPanels, /editRow: \{ gap: 0 \}/);
  assertSourceDoesNotMatch(sharedEntityPanels, /editRow: \{[^}]*minHeight/);
  assertSourceMatch(sharedEntityPanels, /<PanelHeaderCell \{\.\.\.sorting\} sortKey="prepared" style=\{styles\.preparationValue\}>Listo<\/PanelHeaderCell>/);
  assertSourceDoesNotMatch(mealAdherence, /statusLabel|styles\.status/);
  assertSourceDoesNotMatch(mealAdherence, /Cumplimiento actualizado|Nota guardada|statusSaved|noteSaved/);
  assertSourceDoesNotMatch(mealAdherence, /label=\{editingNote \? "Guardar nota" : "Editar nota"\}/);
  assertSourceMatch(mealAdherence, /completionLabel: \{[^}]*fontSize: 15/);

  const mealCompletionSummary = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/meal-completion-summary.tsx"),
    "utf8",
  );
  assertSourceMatch(mealCompletionSummary, /Cumplimiento comidas/);
  assertSourceMatch(mealCompletionSummary, /<CheckCheck color=\{tokens\.color\.textMain\}[^>]*\/>[\s\S]*<Text style=\{styles\.label\}>Cumplimiento comidas/);
  assertSourceMatch(mealCompletionSummary, /label: \{[^}]*fontSize: 15/);
  assertSourceMatch(mealCompletionSummary, /item\.status === "completed"/);
  assertSourceMatch(mealCompletionSummary, /checkCircleCompleted: \{ backgroundColor: tokens\.color\.meal \}/);
  assertSourceMatch(mealCompletionSummary, /checkCirclePending: \{ backgroundColor: tokens\.color\.borderDefault \}/);
  assertSourceMatch(mealCompletionSummary, /completed \? tokens\.color\.entityIconForeground : tokens\.color\.textMuted/);
  assertSourceMatch(mealCompletionSummary, /surface: \{ backgroundColor: `\$\{tokens\.color\.meal\}1A`, borderColor: `\$\{tokens\.color\.meal\}B3`, borderRadius: tokens\.radius\.lg, borderWidth: 1/);
  assertSourceMatch(mealCompletionSummary, /checks: \{[^}]*gap: tokens\.spacing\.xs/);
  assertSourceMatch(mealCompletionSummary, /marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceMatch(mealCompletionSummary, /minHeight: 54/);

  const activeProgram = await readTestFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  assertSourceMatch(activeProgram, /<SectionPageHeader countLabel="semanas" section="calendarization" title="Mi programa activo" \/>/);
  assertSourceDoesNotMatch(activeProgram, /<SectionPageHeader count=\{weekCount\}/);
  assertSourceDoesNotMatch(activeProgram, /<CollectionPageHeader/);

  const appNavigation = await readTestFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  assertSourceMatch(appNavigation, /program: CalendarClock/);
  assertSourceMatch(appNavigation, /pathname\.startsWith\("\/program"\).*icon: CalendarClock/);
  assertSourceMatch(activeProgram, /stickyHeaderIndices=\{\[1\]\}/);
  assertSourceDoesNotMatch(activeProgram, /weekTabsStickyPinned/);
  assertSourceMatch(activeProgram, /program\?\.weeks_count/);
  assertSourceMatch(activeProgram, /Array\.from\(\{ length: weekCount \}/);
  assertSourceMatch(activeProgram, /<ProgramWeekTabs activeWeek=\{activeWeek\}/);
  assertSourceMatch(activeProgram, /<CalendarizedProgramPlanning days=\{programDays\} initialWeek=\{activeWeek\} key=\{`\$\{calendarization\.id\}:\$\{activeWeek\}`\} showWeekTabs=\{false\} weeksData=\{program\.weeks\} \/>/);
  assertSourceMatch(activeProgram, /<ProgramActiveOverview[\s\S]*<ProgramSectionHeader icon=\{Calendar1\} subtitle="Recorre las semanas de tu programa y conoce los planes diarios y alimentos de cada una de ellas\." title="Planificación Semanal" \/>/);
  assertSourceDoesNotMatch(activeProgram, /SectionDivider|SectionHeading|planningDivider/);
  assertSourceDoesNotMatch(activeProgram, /DetailLinkRow|Ver plantilla original/);
  assertSourceMatch(activeProgram, /onOpenOriginalProgram=\{calendarization\?\.source_program_id \? \(\) => router\.push/);
  assertSourceDoesNotMatch(activeProgram, /conserva lo que realmente ocurrió/);
  const programSectionHeader = await readTestFile(path.resolve(process.cwd(), "src/components/programs/program-section-header.tsx"), "utf8");
  assertSourceMatch(programSectionHeader, /<Icon color=\{tokens\.color\.textMain\} size=\{19\} strokeWidth=\{2\.2\} \/>/);
  assertSourceMatch(programSectionHeader, /header: \{[^}]*marginBottom: tokens\.spacing\.sm[^}]*marginTop: tokens\.spacing\.xxl/);
  assertSourceMatch(programSectionHeader, /title: \{[^}]*fontSize: 20[^}]*fontWeight: tokens\.weight\.extraBold/);
  assertSourceMatch(programSectionHeader, /subtitle: \{[^}]*fontSize: tokens\.type\.caption[^}]*lineHeight: 20/);

  const activePlanningControls = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/program-planning-controls.tsx"), "utf8");
  assertSourceMatch(activePlanningControls, /<ScrollableTabBar/);
  assertSourceMatch(activePlanningControls, /tabs=\{weeks\.map/);

  const calendarizedPlanningActive = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedPlanningActive, /compactMonthLabel\(day\.calendar_date\)/);
  assertSourceMatch(calendarizedPlanningActive, /left\.calendar_date\.localeCompare\(right\.calendar_date\)/);
  assertSourceMatch(calendarizedPlanningActive, /pickerHref\("dailyplan-to-calendarized-day", \{ dayId:/);
  assertSourceMatch(calendarizedPlanningActive, /label="Cambiar plan diario"/);

  const activeProgramOverview = await readTestFile(
    path.resolve(process.cwd(), "src/components/programs/program-active-card.tsx"),
    "utf8",
  );
  assertSourceMatch(activeProgramOverview, /<ProgramActiveKpis[^>]*standalone/);
  assertSourceMatch(activeProgramOverview, /<ProgramActiveKpis[^>]*topInset=\{!embedded\}/);
  assertSourceMatch(activeProgramOverview, /<ProgramActiveKpis[^>]*mutedPanels=\{embedded\}/);
  assertSourceDoesNotMatch(activeProgramOverview, /<ProgramActiveKpis[^>]*bleed=\{false\}/);
  assertSourceMatch(activeProgramOverview, /eyebrow="Programa activo"/);
  assertSourceDoesNotMatch(activeProgramOverview, /eyebrow="Programa en curso"/);
  assertSourceDoesNotMatch(activeProgramOverview, /Métricas de activación|SectionHeading|Activity/);
  assertSourceMatch(activeProgramOverview, /embedded \? <DetailLinkRow[\s\S]*router\.push\("\/program" as Href\)/);
  assertSourceMatch(activeProgramOverview, /activeIndicators = program\.indicators\.map/);
  assertSourceMatch(activeProgramOverview, /indicator\.icon === "week"[\s\S]*?icon: undefined[\s\S]*?Number\(indicator\.value\) === 1 \? "SEMANA" : "SEMANAS"/);
  assertSourceMatch(activeProgramOverview, /eyebrowAccessory=\{<HeaderMetadataChip kind="date" value=\{`\$\{compactDateLabel\(calendarization\.start_date\)\} — \$\{compactDateLabel\(calendarization\.end_date\)\}`\} \/>\}/);
  assertSourceMatch(activeProgramOverview, /indicators=\{activeIndicators\}/);
  assertSourceDoesNotMatch(activeProgramOverview, /indicators=\{embedded \? undefined/);
  assertSourceMatch(activeProgramOverview, /export function ProgramActiveHomeOverview[\s\S]*<ProgramActiveOverview \{\.\.\.props\} embedded/);
  assertSourceMatch(activeProgramOverview, /embedded[\s\S]*<Card accent=\{tokens\.color\.program\} style=\{styles\.content\}>\{content\}<\/Card>/);

  const activeProgramKpis = await readTestFile(
    path.resolve(process.cwd(), "src/components/programs/program-active-kpis.tsx"),
    "utf8",
  );
  assertSourceDoesNotMatch(activeProgramKpis, /periodRow|periodDates|CalendarDays/);
  assertSourceDoesNotMatch(activeProgramKpis, /kcalSurface|kcalBorder|periodBorder|periodText/);
  assertSourceMatch(activeProgramKpis, /indicatorsSurfaceReset:\{[^}]*padding:tokens\.spacing\.xs/);
  assertSourceMatch(activeProgramKpis, /standaloneTopInset:\{marginTop:tokens\.spacing\.sm\}/);
  assertSourceMatch(activeProgramKpis, /Planes diarios recorridos/);
  assertSourceMatch(activeProgramKpis, /Cumplimiento comidas/);
  assertSourceMatch(activeProgramKpis, /indicator:\{[^}]*paddingHorizontal:tokens\.spacing\.md[^}]*paddingVertical:tokens\.spacing\.lg/);
  assertSourceMatch(activeProgramKpis, /function ProgressRing/);
  assertSourceMatch(activeProgramKpis, /strokeDashoffset=\{dashOffset\}/);
  assertSourceMatch(activeProgramKpis, /strokeLinecap="round"/);
  assertSourceMatch(activeProgramKpis, /transform=\{`rotate\(-90 \$\{RING_CENTER\} \$\{RING_CENTER\}\)`\}/);
  assertSourceMatch(activeProgramKpis, /indicatorIdentity:\{[^}]*flexDirection:"column"[^}]*justifyContent:"center"/);
  assertSourceMatch(activeProgramKpis, /indicator:\{[^}]*borderRadius:tokens\.radius\.panel/);
  assertSourceMatch(activeProgramKpis, /indicatorLabel:\{[^}]*fontSize:18[^}]*textAlign:"center"/);
  assertSourceDoesNotMatch(activeProgramKpis, /progressRing:\{[^}]*marginTop/);
  assertSourceMatch(activeProgramKpis, /fraction:\{[^}]*fontSize:tokens\.type\.title/);
  assertSourceMatch(activeProgramKpis, /percentageText:\{[^}]*fontSize:tokens\.type\.body/);
  assertSourceMatch(activeProgramKpis, /percentageText:\{[^}]*color:tokens\.color\.textMuted/);
  assertSourceMatch(activeProgramKpis, /<ProgressRing color=\{tokens\.color\.dailyPlan\} current=\{elapsedDays\} percentage=\{advancement\} total=\{totalDays\} trackColor=\{`\$\{tokens\.color\.dailyPlan\}33`\} \/>/);
  assertSourceMatch(activeProgramKpis, /<ProgressRing color=\{tokens\.color\.meal\} current=\{adheredDays\} percentage=\{compliance\} total=\{plannedAdherenceDays\} trackColor=\{`\$\{tokens\.color\.meal\}33`\} \/>/);
  assertSourceMatch(activeProgramKpis, /stroke=\{trackColor\}/);
  assertSourceDoesNotMatch(activeProgramKpis, /styles\.track|styles\.fill/);
  assertSourceDoesNotMatch(activeProgramKpis, /indicator:\{[^}]*borderWidth/);
  assertSourceMatch(activeProgramKpis, /mutedPanels \? styles\.indicatorMuted : styles\.indicatorCard/);
  assertSourceMatch(activeProgramKpis, /indicatorCard:\{backgroundColor:tokens\.color\.surfaceCard\}/);
  assertSourceMatch(activeProgramKpis, /indicatorMuted:\{backgroundColor:tokens\.color\.surfaceMuted\}/);
  assertSourceDoesNotMatch(activeProgramKpis, /indicatorElapsed:\{[^}]*borderColor|indicatorAdherence:\{[^}]*borderColor/);
  assertSourceDoesNotMatch(activeProgramKpis, /percentageTag/);

  const activateProgram = await readTestFile(
    path.resolve(process.cwd(), "src/app/program/activate.tsx"),
    "utf8",
  );
  assertSourceMatch(activateProgram, /stickyHeaderIndices=\{\[0\]\}/);
  assertSourceMatch(activateProgram, /<PickerEntryTabs[\s\S]*createLabel="Crear Nuevo"/);
  assertSourceMatch(activateProgram, /accessibilityLabel="Buscar programa"/);
  assertSourceMatch(activateProgram, /\/api\/v1\/library\/programs\/calendarization-options\?limit=100/);
  assertSourceMatch(activateProgram, /pathname: "\/libraries\/create", params: \{ entity: "program" \}/);
  assertSourceMatch(activateProgram, /<ProgramChildCard[\s\S]*openActionLabel="Seleccionar"/);
  assertSourceDoesNotMatch(activateProgram, /openActionLabel="Cambiar selección"/);
  assertSourceMatch(activateProgram, /<SectionHeading title="Configura la selección" \/>[\s\S]*<NotificationToggle[\s\S]*label="Aviso inicial del plan diario"[\s\S]*<NotificationToggle[\s\S]*label="Avisos según la hora de cada comida"/);
  assertSourceMatch(activateProgram, /label="Calendarizar programa"/);
  assertSourceDoesNotMatch(activateProgram, /<Card accent=\{tokens\.color\.program\}>/);
  assertSourceDoesNotMatch(activateProgram, /PASO 3 DE 3|Confirma la calendarización|Volver a configurar/);

  const todayScreen = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  assertSourceMatch(todayScreen, /<CurrentWeekSection localDate=\{today\.local_date\} \/>[\s\S]*?style=\{styles\.greetingTitle\}>\{`Vamos, \$\{firstName\}`\}[\s\S]*?Fallar en planificar, es planificar fallar/);
  assertSourceMatch(todayScreen, /greetingSubtitle: \{[^}]*marginTop: tokens\.spacing\.xs/);
  assertSourceMatch(todayScreen, /<Chip borderColor=\{planContext\.color\} label=\{planContext\.label\} textColor=\{tokens\.color\.textMain\} \/>/);
  assert.ok(todayScreen.indexOf("<CurrentWeekSection") < todayScreen.indexOf("<CalendarizedDailyPlanCard"));
  assertSourceMatch(todayScreen, /<CurrentWeekSection[\s\S]*?<HomeSectionTitle>Tu plan de alimentos para hoy<\/HomeSectionTitle>[\s\S]*?<CalendarizedDailyPlanCard/);
  assertSourceMatch(todayScreen, /eyebrow="PLAN DEL DÍA"/);
  assertSourceMatch(todayScreen, /greetingRow: \{ gap: 0, marginBottom: 0 \}/);
  assertSourceMatch(todayScreen, /weekRow: \{ marginBottom: tokens\.spacing\.sm \}/);
  assert.ok(todayScreen.indexOf("<CalendarizedDailyPlanCard") < todayScreen.indexOf("<ProgramActiveHomeOverview"));
  assertSourceMatch(todayScreen, /<CalendarizedDailyPlanCard[\s\S]*?<ActiveProgramSectionHeader \/>[\s\S]*?<ProgramActiveHomeOverview/);
  assertSourceMatch(todayScreen, /<CalendarClock color=\{tokens\.color\.textMain\} size=\{19\} strokeWidth=\{2\.2\} \/>/);
  assertSourceMatch(todayScreen, /Tu programa en curso/);
  assertSourceMatch(todayScreen, /Tu plan de hoy pertenece a este programa en curso\. Revisa tu adherencia y consulta los otros planes de tu programa\./);
  assertSourceMatch(todayScreen, /activeProgramSectionTitle: \{[^}]*fontSize: 20[^}]*fontWeight: tokens\.weight\.extraBold/);
  assertSourceMatch(todayScreen, /activeProgramSectionHeader: \{[^}]*marginTop: tokens\.spacing\.xxl/);
  assertSourceMatch(todayScreen, /homeSectionTitle: \{[^}]*fontSize: 18[^}]*marginBottom: 0[^}]*marginTop: tokens\.spacing\.sm/);
  assertSourceDoesNotMatch(todayScreen, /<SectionDivider \/>/);
  const currentWeek = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/current-week-section.tsx"),
    "utf8",
  );
  assertSourceDoesNotMatch(currentWeek, /Semana en curso|<SectionHeading/);
  assertSourceMatch(currentWeek, /<Text[^>]*styles\.monthLabel[^>]*>\{day\.monthLabel\}<\/Text>/);
  assertSourceMatch(currentWeek, /dayCircle: \{[^}]*backgroundColor: tokens\.color\.surfaceCard[^}]*height: 44[^}]*width: 44/);
  assertSourceMatch(currentWeek, /monthLabel: \{[^}]*fontFamily: font\.regular[^}]*fontSize: 9[^}]*fontWeight: tokens\.weight\.medium[^}]*lineHeight: 10/);
  assertSourceMatch(currentWeek, /monthLabelToday: \{ color: tokens\.color\.surfaceApp, fontWeight: tokens\.weight\.semibold \}/);
  assertSourceMatch(currentWeek, /<WeekDaySelectionRing \/>/);
  assertSourceMatch(currentWeek, /dayCircleToday: \{ backgroundColor: tokens\.color\.entityIconForeground \}/);
  assertSourceMatch(currentWeek, /dayNumberToday: \{ color: tokens\.color\.surfaceApp, fontWeight: tokens\.weight\.bold \}/);
  assertSourceMatch(currentWeek, /compact && styles\.dayCircleCompact/);
  assertSourceMatch(currentWeek, /dayCircleCompact: \{ height: 40, width: 40 \}/);
  const weekDayGrid = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/week-day-grid.tsx"),
    "utf8",
  );
  assertSourceMatch(weekDayGrid, /const compactWeekDayWidth = 350/);
  assertSourceMatch(weekDayGrid, /grid: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceMatch(weekDayGrid, /gridCompact: \{ gap: tokens\.spacing\.xs \}/);
  assertSourceMatch(weekDayGrid, /cell: \{[^}]*flex: 1[^}]*gap: tokens\.spacing\.sm/);
  assertSourceMatch(weekDayGrid, /<LinearGradient id=\{gradientId\}[\s\S]*tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat/);
  assertSourceMatch(weekDayGrid, /strokeWidth="6"/);
  assertSourceMatch(weekDayGrid, /selectionRing: \{ bottom: -7, left: -7[^}]*right: -7, top: -7 \}/);
  assertSourceMatch(gallery, /key: "calendars", label: "Calendarios"/);
  assertSourceMatch(gallery, /\{ label: "iPhone XR", width: 414 \}/);
  assertSourceMatch(gallery, /\{ label: "Teléfono compacto", width: 375 \}/);
  assertSourceMatch(gallery, /<CurrentWeekSection localDate="2026-09-01" \/>/);
  assertSourceMatch(gallery, /title="Vamos, Felipe"/);
  assertSourceMatch(gallery, /<GuideMetric label="Peso actual" value="85,0kg" \/>/);
  assertSourceMatch(gallery, /<ProgramDaySelector/);
  assertSourceMatch(gallery, /MI PROGRAMA ACTIVO · FECHAS \+ PLANES/);
  assertSourceMatch(todayScreen, /<ProgramActiveHomeOverview/);
  assertSourceMatch(todayScreen, /greetingHeading: \{ alignItems: "center", flexDirection: "row"/);
  assertSourceMatch(todayScreen, /<GuideMetric onPress=\{\(\) => router\.push\("\/weight" as Href\)\} tone="ppk" value=\{`\$\{displayWeight\(currentWeightKg\)\} kg`\} \/>/);
  assertSourceDoesNotMatch(todayScreen, /<GuideMetric icon="weight"/);
  assertSourceDoesNotMatch(todayScreen, /GuideMetric label="Peso actual"/);
  assertSourceMatch(productUiSourceForIndicators, /guideMetricValueOnly: \{ borderRadius: tokens\.radius\.lg, minHeight: 40 \}/);
  assertSourceMatch(productUiSourceForIndicators, /guideMetricPpk: \{ backgroundColor: "transparent", borderColor: tokens\.color\.borderDefault, borderRadius: tokens\.radius\.pill/);
  assertSourceMatch(productUiSourceForIndicators, /guideMetricValuePpk: \{ color: tokens\.color\.textMain, fontSize: 15, lineHeight: 18 \}/);
  assertSourceDoesNotMatch(productUiSourceForIndicators, /icon === "weight"/);
  assertSourceMatch(todayScreen, /apiRequest<HomeData>\("\/api\/v1\/home"\)/);
  assertSourceMatch(todayScreen, /home\.latest_weight\?\.weight_kg/);
  assertSourceMatch(todayScreen, /latestWeightKg \?\? profile\?\.current_weight_kg \?\? today\?\.measurements\?\.latest_weight_kg/);
  assertSourceMatch(todayScreen, /displayWeight\(currentWeightKg\)/);
  assertSourceMatch(todayScreen, /dateLabel=\{compactDateLabel\(today\.local_date\)\}/);
  assertSourceMatch(todayScreen, /<HomeLibraryGrid counts=\{libraryCounts\} \/>/);
  assertSourceMatch(todayScreen, /home\.library_counts\.program/);
  assertSourceDoesNotMatch(todayScreen, /Propuestas para revisar|pendingProposalCount|setPendingProposalCount/);
  const homeLibraryGrid = await readTestFile(
    path.resolve(process.cwd(), "src/components/home/home-library-grid.tsx"),
    "utf8",
  );
  assertSourceMatch(homeLibraryGrid, /<Bookmark[^>]*>[\s\S]*Mis librerías/);
  assertSourceMatch(homeLibraryGrid, /flexWrap: "wrap"/);
  assertSourceMatch(homeLibraryGrid, /Mis Programas\\nSemanales/);
  assertSourceMatch(homeLibraryGrid, /Mis Planes\\nDiarios/);
  assertSourceMatch(homeLibraryGrid, /Mis Comidas/);
  assertSourceMatch(homeLibraryGrid, /Mis Alimentos/);
  assertSourceMatch(homeLibraryGrid, /pathname: "\/libraries\/create", params: \{ entity: entry\.entity \}/);
  assertSourceMatch(homeLibraryGrid, /section: \{[^}]*marginHorizontal: -tokens\.spacing\.screen[^}]*marginTop: tokens\.spacing\.xxl/);
  assertSourceDoesNotMatch(homeLibraryGrid, /SectionDivider|sectionDivider/);
  assertSourceMatch(homeLibraryGrid, /padding: tokens\.card\.outerPadding/);
  assertSourceMatch(homeLibraryGrid, /borderTopColor: tokens\.color\[entry\.entity\]/);
  assertSourceMatch(homeLibraryGrid, /borderTopWidth: 3/);
  assertSourceMatch(homeLibraryGrid, /title: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceDoesNotMatch(homeLibraryGrid, /description:/);
  assertSourceDoesNotMatch(todayScreen, /<ProgramActiveCard/);
  assertSourceDoesNotMatch(todayScreen, /todayProgramDay|position=\{todayProgramDay/);
  assertSourceDoesNotMatch(activeProgram, /program\?\.days\.map/);

  const libraryDetail = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryDetail, /<ProgramDetailPreview[\s\S]*?scrollable\s*\/>/);
  assertSourceMatch(libraryDetail, /FoodPanels, GroupedFoodsCard, MealPanels.*from "@\/components\/panels"/);
  assertSourceMatch(libraryDetail, /<ProgramSectionHeader icon=\{Utensils\}[^>]*title="Detalle de cada Comida" \/><DailyPlanMealCards/);
  assertSourceMatch(libraryDetail, /<ProgramSectionHeader icon=\{Carrot\}[^>]*title="Alimentos en este plan diario" \/><GroupedFoodsCard/);
  assertSourceMatch(libraryDetail, /hasMealTimeContext[\s\S]*?\? \{ icon: "clock", label: "Cambiar hora"/);
  assertSourceMatch(libraryDetail, /eyebrowAccessory=\{item\.entity === "meal" && hasMealTimeContext && contextTime \? <HeaderMetadataChip kind="time" value=\{contextTime\} \/> : undefined\}/);
  assertSourceMatch(libraryDetail, /item\?\.entity === "dailyPlan"[\s\S]*?\{ icon: "pin", label: isPinnedPlan \? "Dejar de fijar como Plan de hoy" : "Fijar como Plan de hoy"/);
  assertSourceMatch(libraryDetail, /item\?\.entity === "program"[\s\S]*?\{ icon: "calendar-clock", label: "Calendarizar este programa"/);
  assertSourceMatch(libraryDetail, /Alert\.alert\([\s\S]*?\? "¿Fijar este plan para hoy\?" : "¿Dejar de fijar este plan\?"/);
  assertSourceMatch(libraryDetail, /<Button bleed label="Calendarizar este programa"/);
  assertSourceMatch(libraryDetail, /<Button bleed label=\{isPinnedPlan \? "Dejar de fijar como Plan de hoy" : "Fijar como Plan de hoy"\}/);
  assertSourceMatch(libraryDetail, /mealTimeInMenu=\{false\}/);

  assertSourceMatch(appNavigation, /headerPresentation\.secondaryAction[\s\S]*<Pin/);
  assertSourceMatch(appNavigation, /headerPresentation\.secondaryAction[\s\S]*<CalendarClock/);
  assertSourceMatch(appNavigation, /headerPresentation\.secondaryAction[\s\S]*<Clock3/);

  const calendarizedDayDetail = await readTestFile(
    path.resolve(process.cwd(), "src/app/program/days/[id].tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedDayDetail, /<GroupedFoodsCard items=\{foods\} onOpenItem=[\s\S]*?title="Alimentos plan diario"/);
  assertSourceMatch(calendarizedDayDetail, /<MealPanels\s+editing=\{\{/);
  assertSourceMatch(calendarizedDayDetail, /relationKey: meal\.id/);
  assertSourceMatch(calendarizedDayDetail, /\/meals\/order/);
  assertSourceMatch(calendarizedDayDetail, /afterNutrition=\{<DailyMealCompletionCard mealExecution=\{day\.meal_execution\} mealKeys=\{meals\.map\(\(meal\) => meal\.key\)\} \/>\}/);
  assertSourceMatch(calendarizedDayDetail, /eyebrowAccessory=\{<HeaderMetadataChip kind="date" value=\{compactDateLabel\(day\.calendar_date\)\} \/>\}/);
  assertSourceDoesNotMatch(calendarizedDayDetail, /label: "posición"/);
  assertSourceMatch(calendarizedDayDetail, /afterNutrition=\{mealKey \? <MealCompletionToggleCard/);
  assertSourceMatch(calendarizedDayDetail, /eyebrowAccessory=\{meal\.hour \? <HeaderMetadataChip kind="time" value=\{meal\.hour\.slice\(0, 5\)\} \/> : undefined\}/);
  assertSourceMatch(calendarizedDayDetail, /onToggleCompleted=\{\(mealKey, completed\) => void toggleMealCompletion\(mealKey, completed\)\}/);
  assertSourceMatch(calendarizedDayDetail, /action: completed \? "completed" : "skipped"/);
  assertSourceMatch(calendarizedDayDetail, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assertSourceMatch(calendarizedDayDetail, /<ProgramSectionHeader icon=\{Utensils\}[^>]*title="Detalle de cada Comida"/);
  assertSourceMatch(calendarizedDayDetail, /snapshotDailyPlanFoodPanelItems\(meals\)/);
  assertSourceMatch(calendarizedDayDetail, /<ProgramSectionHeader icon=\{Carrot\}[^>]*title="Alimentos en este plan diario"[\s\S]*<GroupedFoodsCard items=\{foods\} onOpenItem=/);

  assertSourceMatch(sharedEntityPanels, /PanelItemName\(\{ item, itemNameStyle, showFoodPortion = false, style = styles\.gridLeadingCell \}/);
  assertSourceMatch(sharedEntityPanels, /<PanelItemName item=\{item\} itemNameStyle=\{styles\.quantityItemText\} style=\{styles\.quantityLeadingCell\} \/>/);
  assertSourceMatch(sharedEntityPanels, /showFoodPortion \? <Text style=\{styles\.foodPortionSuffix\}> \{`\(\$\{decimal\(item\.quantity\)\}\$\{item\.quantityUnit\}\)`\}<\/Text> : null/);
  assertSourceMatch(sharedEntityPanels, /foodPortionSuffix: \{ color: tokens\.color\.textMuted, fontStyle: "italic"/);
  assertSourceMatch(sharedEntityPanels, /<PanelItemName item=\{item\} showFoodPortion=\{leadingLabel === "Alimentos"\}/);
  assertSourceMatch(sharedEntityPanels, /styles\.editName\]\}>\{item\.name\}<Text style=\{styles\.foodPortionSuffix\}>/);
  assertSourceMatch(sharedEntityPanels, /quantityLeadingCell: \{[^}]*flex: 1/);
  assertSourceMatch(sharedEntityPanels, /quantityValue: \{ textAlign: "center", width: 56 \}/);
  assertSourceMatch(sharedEntityPanels, /function PanelHeaderCell/);
  assertSourceMatch(sharedEntityPanels, /headerCell: \{[^}]*alignSelf: "stretch"[^}]*justifyContent: "center"/);
  assertSourceMatch(sharedEntityPanels, /<PanelHeaderCell \{\.\.\.sorting\} align="left" sortKey="name" style=\{styles\.gridLeadingCell\}>\{leadingLabel\}<\/PanelHeaderCell>/);
  assertSourceDoesNotMatch(sharedEntityPanels, /<Text style=\{\[styles\.headerText, styles\.gridLeadingCell/);
  assertSourceDoesNotMatch(sharedEntityPanels, /styles\.name, styles\.gridLeadingCell/);

  const comparisonComponents = await readTestFile(
    path.resolve(process.cwd(), "src/components/comparisons/comparison-components.tsx"),
    "utf8",
  );
  assertSourceMatch(comparisonComponents, /name: item\.name,/);
  assertSourceDoesNotMatch(comparisonComponents, /name: item\.quantity == null \? item\.name/);

  assertSourceMatch(libraryEntityPanels, /FoodPanels as SharedFoodPanels/);
  assertSourceMatch(libraryEntityPanels, /MealPanels as SharedMealPanels/);
  assertSourceMatch(libraryEntityPanels, /return <SharedFoodPanels editing=\{editing\} items=\{items\.map\(toFoodPanelItem\)\} nestedScroll=\{nestedScroll\} onOpenItem=/);
  assertSourceMatch(libraryEntityPanels, /return <SharedMealPanels editing=\{editing\} items=\{items\.map\(toMealPanelItem\)\} nestedScroll=\{nestedScroll\} onOpenItem=/);

  const calendarizationAdapters = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/presentation-adapters.ts"),
    "utf8",
  );
  assertSourceMatch(calendarizationAdapters, /export function snapshotDailyPlanFoodPanelItems/);
  assertSourceMatch(calendarizationAdapters, /current\.quantity \+= food\.quantity_g \?\? 0/);
  assertSourceMatch(calendarizationAdapters, /food\.protein_per_kilogram\s*\?\?/);

  const sectionDivider = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/section-divider.tsx"),
    "utf8",
  );
  assertSourceMatch(sectionDivider, /export function SectionDivider/);
  assertSourceMatch(sectionDivider, /divider: \{[^}]*marginBottom: tokens\.spacing\.sm[^}]*marginTop: tokens\.spacing\.lg/);
  assertSourceMatch(sectionDivider, /divider: \{[^}]*marginHorizontal: -tokens\.spacing\.screen/);
  assertSourceMatch(gallery, /title="Separador de secciones"/);

  const entityDetail = await readTestFile(
    path.resolve(process.cwd(), "src/components/details/entity-detail-page.tsx"),
    "utf8",
  );
  const pageCardStyle = entityDetail.match(/pageCard: \{([^}]+)\}/)?.[1] ?? "";
  assertSourceDoesNotMatch(pageCardStyle, /backgroundColor/);
  assertSourceDoesNotMatch(pageCardStyle, /border(?:Color|Radius|TopWidth|Width)/);
  assertSourceDoesNotMatch(pageCardStyle, /padding(?:Top|:)/);
  assertSourceDoesNotMatch(entityDetail, /borderTopColor: tokens\.color\[entity\]/);

  const programDailyPlan = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"),
    "utf8",
  );
  assertSourceMatch(programDailyPlan, /day \? \(day\.meals \?\? \[\]\)\.map\(mealPanelItem\) : meals/);
  assertSourceMatch(programDailyPlan, /const openDetailLabel = `Ir al detalle del plan de \$\{dayLabel\}`/);
  assertSourceMatch(programDailyPlan, /label=\{openDetailLabel\}/);
  assertSourceMatch(programDailyPlan, /headingLink=\{openDetail \? \{ label: openDetailLabel, onPress: openDetail \} : undefined\}/);
  assertSourceMatch(programDailyPlan, /router\.push\(`\/libraries\/daily-plans\/\$\{day\.dailyplan_id\}` as Href\)/);
  assertSourceMatch(programDailyPlan, /const openDetail = onOpen \?\? \(day\?\.dailyplan_id \?/);
  assertSourceMatch(programDailyPlan, /actions=\{\(/);
  assertSourceDoesNotMatch(programDailyPlan, /accessory=\{\(/);
  assertSourceDoesNotMatch(programDailyPlan, /kpiVariant="nested"|subtitle="Plan diario asignado"|label: "plan asignado"/);
  assertSourceMatch(programDailyPlan, /label: "posición"/);
  assertSourceMatch(programDailyPlan, /icon: "meal", label: "comidas"/);
  assertSourceMatch(programDailyPlan, /onOpenItem=\{\(meal\) =>/);

  const productUiSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  const cardSurfaceSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/surfaces.tsx"),
    "utf8",
  );
  const legacyPrimitivesSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/primitives.tsx"),
    "utf8",
  );
  const controlsSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/controls.tsx"),
    "utf8",
  );
  assertSourceMatch(controlsSource, /export function SystemSwitch[\s\S]*accessibilityRole="switch"[\s\S]*accessibilityState=\{\{ checked: value, disabled \}\}[\s\S]*onPress=\{\(\) => onValueChange\(!value\)\}/);
  assertSourceMatch(controlsSource, /systemSwitch: \{[^}]*height: 28[^}]*width: 48/);
  assertSourceMatch(controlsSource, /systemSwitchActive: \{ backgroundColor: tokens\.color\.success \}/);
  assertSourceMatch(controlsSource, /systemSwitchKnobActive: \{ transform: \[\{ translateX: 20 \}\] \}/);
  assertSourceMatch(legacyPrimitivesSource, /button: \{[^}]*minHeight: 48/);
  assertSourceDoesNotMatch(controlsSource, /button: \{[^}]*minHeight: 54|trackColor|thumbColor|ios_backgroundColor/);
  assertSourceDoesNotMatch(legacyPrimitivesSource, /button: \{[^}]*minHeight: 54/);
  assertSourceMatch(cardSurfaceSource, /card: \{[^}]*marginHorizontal: -tokens\.spacing\.screen/);
  assertSourceMatch(legacyPrimitivesSource, /card: \{[^}]*marginHorizontal: -tokens\.spacing\.screen/);
  assertSourceMatch(productUiSource, /entityCardPressable: \{ marginHorizontal: -tokens\.spacing\.screen \}/);
  assertSourceMatch(productUiSource, /export function EntityCardActions/);
  assertSourceMatch(productUiSource, /export function EntityCardAction/);
  assertSourceMatch(productUiSource, /actions \? styles\.entityCardWithActions : null/);
  assertSourceMatch(productUiSource, /entityCardWithActions: \{ paddingBottom: tokens\.card\.innerPadding \}/);
  assertSourceDoesNotMatch(productUiSource, /entityCardActions: \{[^\n]*marginTop/);
  assertSourceMatch(productUiSource, /entityCardAction: \{ alignItems: "center", borderRadius:/);
  assertSourceDoesNotMatch(productUiSource, /entityCardAction: \{[^\n]*borderWidth/);
  assertSourceMatch(productUiSource, /entityCardPanelSlot: \{ minWidth: 0 \}/);

  const panelSurface = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/panel-surface.tsx"),
    "utf8",
  );
  assertSourceMatch(panelSurface, /marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceMatch(panelSurface, /borderRadius: tokens\.radius\.panel/);
  assertSourceMatch(cardSurfaceSource, /borderRadius: tokens\.radius\.card/);

  assertSourceMatch(gallery, /Siempre abajo y sin bordes/);
  assertSourceMatch(gallery, /EntityCardAction/);

  const programChart = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"),
    "utf8",
  );
  assertSourceMatch(programChart, /import \{ Card, EntityHeading, type EntityHeadingLink, layoutStyles \} from "@\/components\/ui"/);
  assertSourceDoesNotMatch(programChart, /Card.*from "@\/components\/ui\/primitives"/);
  assertSourceMatch(programChart, /<Card accent=\{tokens\.color\.program\}>/);
  assertSourceMatch(programChart, /<ProgramMetricPreview[^\n]*style=\{layoutStyles\.cardContentBleed\}/);
  assertSourceDoesNotMatch(programChart, /footer: \{[^}]*borderTop/);
  assertSourceMatch(programChart, /allocationSlot: \{[^\n]*gap: 2[^\n]*paddingHorizontal: 1/);
  assertSourceMatch(programChart, /allocationSegment: \{ borderRadius: 2/);
  assertSourceMatch(programChart, /key=\{`\$\{index\}-\$\{label\}`\} style=\{styles\.weekLabelCell\}/);
  assertSourceMatch(programChart, /export function programDailyMetricData/);
  assertSourceMatch(programChart, /lastWeek === 1 \? "Semana 1" : `Semanas 1-\$\{lastWeek\}`/);
  assertSourceMatch(programChart, /style=\{\[styles\.axisChip, styles\.axisLeadingChip\]\}/);
  assertSourceMatch(programChart, /axisLeadingChip: \{[^}]*textAlign: "left"[^}]*width: "100%"/);
  assertSourceMatch(programChart, /plotViewportWidth \* Math\.max\(1, axisLabels\.length \/ 8\)/);
  assertSourceMatch(programChart, /<ScrollView[\s\S]*horizontal[\s\S]*showsHorizontalScrollIndicator=\{axisLabels\.length > 8\}/);
  assertSourceMatch(programChart, /index > 0 && index % 7 === 0 && styles\.weekDivider/);
  assertSourceDoesNotMatch(programChart, /weekLabels: \{[^}]*paddingHorizontal/);
  assertSourceDoesNotMatch(programChart, /weekLabels: \{[^}]*gap:/);
  assertSourceMatch(programChart, /weekLabelCell: \{ flex: 1, minWidth: 0, paddingHorizontal: 1 \}/);
  assertSourceMatch(programChart, /\(index \+ 0\.5\) \* \(140 \/ slotCount\)/);
  assertSourceMatch(programChart, /\(index \+ 1\) \* 7 \* \(140 \/ slotCount\)/);
  assertSourceDoesNotMatch(programChart, /metricPlot: \{[^}]*paddingHorizontal/);
  assertSourceMatch(programChart, /metricPlot: \{ backgroundColor: tokens\.color\.surfaceApp/);
  assertSourceMatch(programDetail, /axisLeadingLabel="Semana"/);
  assertSourceMatch(programChart, /weeks\.flatMap\(\(week\) => week\.days\.map/);
  assertSourceMatch(programChart, /axisLabels = \["S1", "S2"\]/);
  assertSourceMatch(programChart, /width < 600[\s\S]*?\? \{ width: "40%" as const \}/);
  assertSourceMatch(programChart, /<Polyline[^\n]*strokeWidth="2"/);
  assertSourceMatch(programChart, /<Stop offset="0" stopColor=\{metric\.color\} stopOpacity=\{0\.44\}/);
  assertSourceMatch(programChart, /<Stop offset="1" stopColor=\{metric\.color\} stopOpacity=\{0\}/);
  assertSourceMatch(programChart, /<LinearGradient gradientUnits="userSpaceOnUse" id=\{`metric-area-\$\{metric\.key\}`\} x1="0" x2="0" y1="0" y2="44">/);
  assertSourceMatch(programChart, /color: tokens\.color\.kcalBorder/);
  assertSourceMatch(programChart, /rangeBadgeCalories: \{ backgroundColor: tokens\.color\.kcalSurface, borderColor: tokens\.color\.kcalBorder, borderWidth: 1 \}/);
  assertSourceMatch(programChart, /<Polygon fill=\{`url\(#metric-area-\$\{metric\.key\}\)`\} points=\{areaPoints\}/);
  assertSourceMatch(programChart, /strokeWidth="3"[^\n]*x1=\{x\} x2=\{x\} y1=\{y\} y2=\{y\}/);
  assertSourceMatch(programChart, /P \{allocationRange\(liveAllocationValues, 0/);
  assertSourceMatch(programChart, /const hasAllocation = protein \+ carbs \+ fat > 0/);
  assertSourceMatch(planningControls, /key=\{day\.id\}/);
  assertSourceMatch(programDetail, /axisLabels=\{\(liveWeeks\.length \? liveWeeks\.map\(\(week\) => week\.week_number\) : displayedWeeks\)\.map\(\(week\) => `S\$\{week\}`\)\}/);
  assertSourceMatch(programDetail, /const liveMetricData = weekData \? programDailyMetricData\(\[weekData\]\) : undefined/);
  assertSourceDoesNotMatch(programDetail, /weekData\.days\.filter\(\(day\) => day\.nutrition\)/);

  const libraryCardSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryCardSource, /programDailyMetricData\(item\.panel\.weeks\)/);
  assertSourceMatch(libraryCardSource, /`S\$\{week\.week_number\}`/);

  const layoutUiSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/layout.tsx"),
    "utf8",
  );
  assertSourceMatch(layoutUiSource, /cardContentBleed: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);

  const controlsUiSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/controls.tsx"),
    "utf8",
  );
  const primitivesUiSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/primitives.tsx"),
    "utf8",
  );
  for (const source of [controlsUiSource, primitivesUiSource]) {
    assertSourceMatch(source, /bleed = true/);
    assertSourceMatch(source, /buttonBleed: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  }

  const programDayPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-day-comparison-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(programDayPanels, /EntityPanelTabs/);
  assertSourceMatch(programDayPanels, /MacroCalorieDistribution/);
  assertSourceMatch(programDayPanels, /PanelAllocationBar/);
  assertSourceMatch(programDayPanels, /<Pencil/);
  assertSourceMatch(programDayPanels, /cell: \{[^}]*fontSize: tokens\.type\.caption/);
  assertSourceMatch(programDayPanels, /planName: \{[^}]*fontSize: tokens\.type\.label/);
  assertSourceDoesNotMatch(programDayPanels, /cell: \{[^}]*fontSize: 11/);
  assertSourceDoesNotMatch(programDayPanels, /<PanelAllocationBar size="compact"/);
  assertSourceMatch(programDayPanels, /<ProteinPerKilogramBadge showUnit=\{false\} style=\{styles\.ppkBadge\}/);
  assertSourceMatch(programDayPanels, /ppkBadge: \{ height: 24, minHeight: 24 \}/);
  assertSourceMatch(programDayPanels, /calorieShareDataCell: \{ flex: 1\.35, maxWidth: "33%" \}/);
  assertSourceMatch(programDayPanels, /ppkDataCell: \{ flex: 0\.65 \}/);
  assertSourceMatch(programDayPanels, /\{ key: "share", label: "% Cal", style: styles\.calorieShareDataCell \}/);
  assertSourceMatch(programDayPanels, /\{ key: "ppk", label: "PpK", style: styles\.ppkDataCell \}/);
  assertSourceMatch(programDayPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assertSourceMatch(programDayPanels, /Header columns=\{\[\{ key: "calories", label: "Cal" \}, \{ key: "share", label: "% Cal"/);
  assertSourceMatch(programDayPanels, /Header columns=\{\[\{ key: "ppk", label: "PpK"/);
  assertSourceMatch(programDayPanels, /Header columns=\{\[\{ key: "protein", label: "P%" \}, \{ key: "carbs", label: "C%" \}, \{ key: "fat", label: "F%" \}, \{ key: "protein", label: "P\|C\|F"/);

  const programMetricPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"),
    "utf8",
  );
  assertSourceMatch(programMetricPanels, /metricTitle: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceMatch(programMetricPanels, /metricIdentity: \{[^}]*height: 58/);
  assertSourceMatch(programMetricPanels, /allocationIdentity: \{ height: 94/);
  assertSourceMatch(programMetricPanels, /rangeBadge: \{[^}]*fontSize: tokens\.type\.label/);
  assertSourceMatch(programMetricPanels, /axisChip: \{[^}]*fontSize: tokens\.type\.label/);
  assertSourceMatch(programMetricPanels, /axisChip: \{[^}]*backgroundColor: "transparent"[^}]*borderColor: tokens\.color\.borderDefault[^}]*borderWidth: 1[^}]*color: tokens\.color\.textMuted/);
  assertSourceMatch(programMetricPanels, /allocationRange: \{[^}]*fontSize: tokens\.type\.label/);
  assertSourceMatch(programMetricPanels, /width < 600[\s\S]*\? \{ width: "40%" as const \}/);

  const productUi = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assertSourceMatch(productUi, /const structuralIndicatorColors/);
  assertSourceMatch(productUi, /food: tokens\.color\.food/);
  assertSourceMatch(productUi, /meal: tokens\.color\.meal/);
  assertSourceMatch(productUi, /dailyPlan: tokens\.color\.dailyPlan/);
  assertSourceDoesNotMatch(productUi, /styles\.structuralDivider/);
});

test("semantic notices use a half-opacity one-pixel border and a ten-percent tone surface", async () => {
  const feedback = await readTestFile(path.resolve(process.cwd(), "src/components/ui/feedback.tsx"), "utf8");
  const primitives = await readTestFile(path.resolve(process.cwd(), "src/components/ui/primitives.tsx"), "utf8");
  const product = await readTestFile(path.resolve(process.cwd(), "src/components/ui/product.tsx"), "utf8");

  for (const source of [feedback, primitives, product]) {
    assertSourceMatch(source, /backgroundColor: `\$\{color\}1A`/);
    assertSourceMatch(source, /borderColor: `\$\{color\}80`/);
    assertSourceDoesNotMatch(source, /borderLeftColor: color/);
  }
  assertSourceMatch(feedback, /notice: \{[^}]*borderWidth: 1/);
  assertSourceMatch(primitives, /notice: \{[^}]*borderWidth: 1/);
  assertSourceMatch(product, /message: \{[^}]*borderWidth: 1/);
  for (const source of [feedback, primitives, product]) {
    assertSourceMatch(source, /tokens\.color\.contextual/);
    assertSourceMatch(source, /borderRadius: tokens\.radius\.panel/);
    assertSourceMatch(source, /marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
    assertSourceMatch(source, /padding: tokens\.card\.outerPadding/);
  }
  assertSourceDoesNotMatch(feedback, /borderLeftWidth/);
  assertSourceDoesNotMatch(primitives, /borderLeftWidth/);
  assertSourceDoesNotMatch(product, /message: \{[^}]*borderLeftWidth/);
});

test("the onboarding gallery exposes every visual journey view without product side effects", async () => {
  const navigation = await readTestFile(path.resolve(process.cwd(), "src/components/dev/gallery-navigation.tsx"), "utf8");
  const journey = await readTestFile(path.resolve(process.cwd(), "src/components/onboarding/onboarding-journey-view.tsx"), "utf8");

  assertSourceMatch(navigation, /\{ key: "onboarding", label: "Onboarding" \}/);
  for (const step of ["login", "value", "structure", "panels", "control", "progress", "disclosures", "goal", "identity", "measurements", "activity", "dietary", "summary", "dailyPlan", "plans"]) {
    assertSourceMatch(journey, new RegExp(`key: "${step}"`));
  }
  assertSourceMatch(journey, /training_frequency/);
  assertSourceMatch(journey, /Cómo leer los paneles/);
  assertSourceMatch(journey, /Continuar con Free/);
  assertSourceMatch(journey, /<SubscriptionPlanCard/);
  assertSourceMatch(journey, /commercialPlanBenefits\[plan\.name\]/);
  assertSourceMatch(journey, /Ver opciones de \$\{plan\.name\}/);
  assertSourceMatch(journey, /Ver precio en la tienda/);
  assertSourceDoesNotMatch(journey, /annualPrice|\$3\.990|\$6\.990/);
  assertSourceMatch(journey, /<SubscriptionPurchaseButton/);
  assertSourceMatch(journey, /<SubscriptionPurchaseButton label="Continuar con Free"/);
  assertSourceMatch(journey, /primary="Generar primer plan"/);
  assertSourceMatch(journey, /storyboardSummaryLayout \? nutritionGoalSection : estimationInformationSection[\s\S]*storyboardSummaryLayout \? maintenanceSection : nutritionGoalSection[\s\S]*storyboardSummaryLayout \? estimationInformationSection : maintenanceSection/);
  assertSourceMatch(journey, /!storyboardSummaryLayout \? <Pressable accessibilityRole="button" onPress=\{controller\.onAdjust \?\? noop\}/);
  assertSourceMatch(journey, /summaryGridPanelBleed: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  assertSourceMatch(journey, /summaryHero: \{[^}]*backgroundColor: tokens\.color\.kcalSurface[^}]*borderColor: tokens\.color\.kcalBorder[^}]*borderRadius: tokens\.component\.nutritionKpi\.regular\.totalRadius[^}]*borderWidth: tokens\.component\.nutritionKpi\.regular\.totalBorderWidth/);
  assertSourceMatch(journey, /summaryHero: \{[^}]*gap: 1[^}]*paddingHorizontal: tokens\.spacing\.sm[^}]*paddingVertical: tokens\.spacing\.sm/);
  assertSourceMatch(journey, /summaryHero: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assertSourceMatch(journey, /summaryGrid: \{[^}]*alignSelf: "stretch"/);
  assertSourceMatch(journey, /summaryCell: \{[^}]*flexBasis: "45%"[^}]*flexGrow: 1[^}]*minWidth: 0/);
  assertSourceMatch(journey, /summaryValue: \{[^}]*fontSize: 34/);
  assertSourceMatch(journey, /summaryQuestion: \{ gap: 7 \}/);
  assertSourceMatch(journey, /styles\.summaryMetricLabel}>Calorías<\/Text>[\s\S]*estimate\?\.estimated_maintenance_kcal[\s\S]*styles\.summaryMetricUnit}>kcal<\/Text>/);
  assertSourceMatch(journey, /<NutritionKpiSection[\s\S]*calories=\{calories\}[\s\S]*perKilogram: estimate\?\.protein_per_kg \?\? 1\.8/);
  assertSourceMatch(journey, /<NutritionKpiSection[\s\S]*<Pressable accessibilityRole="button" onPress=\{controller\.onAdjust \?\? noop\} style=\{styles\.adjustNutritionAction\}>[\s\S]*Ajusta objetivo nutricional[\s\S]*<\/Card>/);
  assertSourceDoesNotMatch(journey, /El mantenimiento usa edad, sexo de cálculo/);
  assertSourceMatch(journey, /function GeneratedDailyPlanView/);
  assertSourceMatch(journey, /screen: \{[^}]*paddingTop: tokens\.spacing\.lg \+ \(tokens\.spacing\.md \* 2\) \+ 18/);
  assertSourceMatch(journey, /topInsetReduction = 0/);
  assertSourceMatch(journey, /index >= 7 && index <= 12 && styles\.profileScreen/);
  assertSourceMatch(journey, /profileScreen: \{ paddingTop: tokens\.spacing\.lg \+ \(tokens\.spacing\.md \* 2\) \+ 18 - 32 \}/);
  assertSourceMatch(journey, /index === 6 \? <CreditContinueButton label=\{primary\} \/> : <Button label=\{primary\} loading=\{controller\.busy\} onPress=\{controller\.onNext \?\? noop\} \/>/);
  assertSourceMatch(journey, /<EntityDetailPage[\s\S]*eyebrow="PLAN DEL DÍA"[\s\S]*title="Plan equilibrado · Día 1"/);
  assertSourceMatch(journey, /<MealPanels items=\{generatedDailyPlanMeals\} showEditTab=\{false\} \/>/);
  assertSourceMatch(journey, /<EntityDetailSection title="Tabla de comparación entre comidas">/);
  assertSourceMatch(journey, /<EntityDetailSection title="Detalle de cada Comida">[\s\S]*<DailyPlanMealDetailList items=\{generatedDailyPlanMealDetails\} \/>/);
  assertSourceDoesNotMatch(journey, /subtitle="Creado a partir de tu objetivo y nivel de actividad"/);
  assertSourceMatch(journey, /id="daily-plan-credit-button"/);
  assertSourceMatch(journey, /<Text style=\{\[styles\.creditContinueLabel, chip && styles\.creditContinueLabelChip\]\}>\{label\}<\/Text>/);
  assertSourceMatch(journey, /if \(index >= 7 && index <= 12\)[\s\S]*index === 12 \? <CreditContinueButton chip label=\{primary\} \/> : <ContinueChip label=\{primary\} \/>/);
  assertSourceMatch(journey, /creditContinueButtonChip: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*minHeight: 34[^}]*paddingHorizontal: tokens\.spacing\.lg/);
  assertSourceMatch(journey, /<ChevronLeft color=\{tokens\.color\.textMuted\} size=\{16\} \/>/);
  assertSourceDoesNotMatch(journey, /<ArrowLeft/);
  assertSourceMatch(journey, /id="activity-selection-border"/);
  assertSourceMatch(journey, /measurementFields: \{ gap: tokens\.spacing\.md \}/);
  assertSourceMatch(journey, /profileQuestion: \{[^}]*color: tokens\.color\.textMain[^}]*fontSize: tokens\.type\.label[^}]*fontWeight: tokens\.weight\.regular[^}]*letterSpacing: 1\.1[^}]*textTransform: "uppercase"/);
  assertSourceMatch(journey, /profileInput: \{ paddingVertical: 0, textAlign: "center", textAlignVertical: "center" \}/);
  assertSourceMatch(journey, /index >= 8 && styles\.profileProgressEyebrowTextMain/);
  assertSourceMatch(journey, /<Text style=\{profileQuestionStyle\}>OBJETIVO NUTRICIONAL PROPUESTO<\/Text>/);
  assertSourceMatch(journey, /profileCard: \{ backgroundColor: "transparent" \}/);
  assertSourceMatch(journey, /summaryCard: \{ marginTop: -tokens\.spacing\.md \}/);
  assertSourceMatch(journey, /function DietaryPreferencesView/);
  assertSourceMatch(journey, /dietaryCard: \{ gap: tokens\.spacing\.xl \}/);
  assertSourceMatch(journey, /title="Preferencias alimentarias"/);
  assertSourceMatch(journey, /Tipo de alimentación/);
  assertSourceMatch(journey, /Alergias o condiciones relevantes/);
  assertSourceMatch(journey, /Alimentos que no consumes/);
  assertSourceMatch(journey, /<ProfileStepLayout index=\{index\} primary="Analizar">/);
  assertSourceMatch(journey, /optionCard: \{[^}]*backgroundColor: "transparent"/);
  assertSourceMatch(journey, /id="activity-radio-credit"/);
  assertSourceMatch(journey, /<CreditSelectionBorder id="goal-option-border" shape="lg" \/>/);
  assertSourceMatch(journey, /id="goal-selection-check"/);
  assertSourceMatch(journey, /<Path d="M3\.5 11\.5 8\.5 16\.5 18\.5 6\.5"[^>]*stroke="url\(#goal-selection-check\)"/);
  assertSourceMatch(journey, /<CreditSelectionBorder id="identity-option-border" shape="pill" \/>/);
  assertSourceMatch(journey, /trainingFrequencyChip: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*flex: 1[^}]*minHeight: 34[^}]*minWidth: 0/);
  assertSourceMatch(journey, /<CreditSelectionBorder id="training-frequency-border" shape="pill" \/>/);
  assertSourceMatch(journey, /<Rect fill="none" height="100%" rx=\{radius\} stroke=\{`url\(#\$\{id\}\)`\} strokeWidth="4" width="100%" \/>/);
  assertSourceMatch(journey, /trainingFrequencyChipSelected: \{[^}]*borderWidth: 0[^}]*overflow: "hidden"/);
  assertSourceMatch(journey, /const selected = controller\.values\.trainingFrequency === value/);
  assertSourceDoesNotMatch(journey, /function HomeView|home: HomeView/);
  assertSourceMatch(journey, /function ExplanationDots/);
  assertSourceMatch(journey, /explanationFooter: \{[^}]*marginBottom: 48/);
  assertSourceMatch(journey, /function ContinueChip/);
  assertSourceMatch(journey, /id="continue-chip-border"/);
  assertSourceMatch(journey, /continueChip: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*minHeight: 34/);
  assertSourceMatch(journey, /continueChipInset: \{[^}]*bottom: 2, left: 2[^}]*right: 2, top: 2/);
  assertSourceMatch(journey, /<Button disabled=\{controller\.loginDisabled\} label="Iniciar sesión o crear cuenta" loading=\{controller\.busy\} multicolorSurface="app" onPress=\{controller\.onLogin \?\? noop\} variant="multicolor" \/>/);
  assertSourceMatch(journey, /explanationFooterWithAction: \{ gap: tokens\.spacing\.xs, marginBottom: 34 \}/);
  assertSourceMatch(journey, /<View style=\{styles\.centeredLogo\}><MyScoopeBrandLogo \/><\/View>/);
  assertSourceMatch(journey, /const isExplanation = index >= 1 && index <= 5/);
  assertSourceMatch(journey, /const usesCenteredTitleSpacing = \(index <= 6 \|\| brandedCentered\) && !externalExplanationChrome/);
  assertSourceMatch(journey, /<StepHeader brandedCentered description="Compara lo que incluyen Free, Basic y Pro/);
  assertSourceMatch(journey, /styles\.introCentered/);
  assertSourceMatch(journey, /styles\.centeredTitleSpacing/);
  assertSourceMatch(journey, /function ProfileProgress/);
  assertSourceMatch(journey, /const isProfileStep = index >= 7 && index <= 12/);
  assertSourceMatch(journey, /index === 6 && styles\.disclosuresEyebrow/);
  assertSourceMatch(journey, /disclosuresEyebrow: \{ color: tokens\.color\.textMuted \}/);
  assertSourceMatch(journey, /!isProfileStep \? <Text style=\{\[styles\.description, isCenteredIntro && styles\.centeredText\]\}>\{description\}<\/Text> : null/);
  assertSourceMatch(journey, /!usesBrandedHeader && !isProfileStep \? <Text/);
  assertSourceMatch(journey, /isProfileStep \? \(!fixedProfileChrome \? <ProfileProgress index=\{index\} \/> : null\) : index === 6 \? null/);
  assertSourceMatch(journey, /<Text style=\{\[styles\.profileProgressEyebrow, index >= 8 && styles\.profileProgressEyebrowTextMain,[^\]]*profileProgressEyebrowBottomSpacing[^\]]*\]\}>OBJETIVO Y PLANIFICACIÓN<\/Text>/);
  assertSourceMatch(journey, /const isCenteredIntro = index <= 12 \|\| brandedCentered/);
  assertSourceMatch(journey, /if \(index >= 7 && index <= 12\)[\s\S]*styles\.profileFooter[\s\S]*styles\.profileBackAction[\s\S]*styles\.profilePrimaryAction/);
  assertSourceMatch(journey, /profileFooter: \{[^}]*flexDirection: "row"[^}]*justifyContent: "space-between"/);
  assertSourceMatch(journey, /creditGradient\("dot", `profile-dot-\$\{stepIndex\}`\)/);
  assertSourceMatch(journey, /creditGradient\("line", `profile-line-\$\{stepIndex\}`\)/);
  assertSourceMatch(journey, /Array\.from\(\{ length: 6 \}/);
  assertSourceMatch(journey, /Paso \$\{activeIndex \+ 1\} de 6 de tu perfil/);
  for (const view of ["IdentityView", "MeasurementsView", "ActivityView", "SummaryView"]) {
    const nextView = view === "IdentityView" ? "MeasurementsView" : view === "MeasurementsView" ? "ActivityView" : view === "ActivityView" ? "SummaryView" : "const plans";
    const section = journey.match(new RegExp(`function ${view}[\\s\\S]*?${nextView}`))?.[0] ?? "";
    assertSourceDoesNotMatch(section, /<Card accent=/);
  }
  for (const [view, nextView] of [["ValueView", "StructureView"], ["PanelsView", "ControlView"], ["ProgressView", "DisclosuresView"]]) {
    const section = journey.match(new RegExp(`function ${view}[\\s\\S]*?function ${nextView}`))?.[0] ?? "";
    assertSourceDoesNotMatch(section, /<Card accent=/);
  }
  assertSourceMatch(journey.match(/function ValueView[\s\S]*?function StructureView/)?.[0] ?? "", /<View style=\{styles\.valueFeatures\}>[\s\S]*?<ExplanationCard[\s\S]*?<ExplanationCard/);
  assertSourceMatch(journey, /explanationSteps\.map\(\(step, dotIndex\) =>/);
  assertSourceMatch(journey, /id="onboarding-credit-gradient"/);
  assertSourceMatch(journey, /fill="url\(#onboarding-credit-gradient\)"/);
  assertSourceDoesNotMatch(journey, /WeekDaySelectionRing/);
  assertSourceDoesNotMatch(journey.match(/function ValueView[\s\S]*?function DisclosuresView/)?.[0] ?? "", /<JourneyFooter/);
  assertSourceMatch(journey, /PanResponder\.create/);
  assertSourceMatch(journey, /Boolean\(controller\) && index >= 1 && index <= 5/);
  assertSourceDoesNotMatch(journey, /OnboardingExplanationCarousel/);
  assertSourceDoesNotMatch(journey.match(/function LoginView[\s\S]*?function ValueView/)?.[0] ?? "", /<Brand|loginKicker|<Card|quietCenter/);
  assertSourceMatch(journey, /loginAction: \{ width: "100%" \}/);
  assertSourceDoesNotMatch(journey, /loginAction: \{[^}]*marginTop: "auto"/);
  assertSourceDoesNotMatch(journey, /useSession|apiRequest|fetch\(|router\.|useRouter/);
  const onboarding = await readTestFile(path.resolve(process.cwd(), "src/app/onboarding.tsx"), "utf8");
  const onboardingPreview = await readTestFile(path.resolve(process.cwd(), "src/app/onboarding-preview.tsx"), "utf8");
  assertSourceMatch(onboarding, /scroll=\{usesFixedDisclosuresFooter \|\| usesFixedProfileChrome \? false : stepIndex >= 6 \? "auto" : false\}/);
  assertSourceMatch(onboarding, /presentationPropsForOnboardingStep\(step\)/);
  assertSourceMatch(onboarding, /<OnboardingJourneyView controller=\{controller\} \{\.\.\.presentationProps\} step=\{step\} \/>/);
  assertSourceMatch(onboarding, /pathname: "\/subscription", params: \{ origin: "onboarding"/);
  const layout = await readTestFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");
  assertSourceMatch(layout, /pathname === "\/subscription" && origin === "onboarding"/);
  assertSourceMatch(onboardingPreview, /scroll=\{usesFixedDisclosuresFooter \|\| usesFixedProfileChrome \? false : stepIndex >= 6 \? "auto" : false\}/);
  const storyboardGallery = await readTestFile(path.resolve(process.cwd(), "src/components/dev/storyboard-gallery.tsx"), "utf8");
  assertSourceMatch(journey, /const onboardingStoryboardTopInsetReduction = 20/);
  assertSourceMatch(journey, /const earlyOnboardingStoryboardTopInsetReduction = onboardingStoryboardTopInsetReduction \+ 18/);
  assertSourceMatch(journey, /findIndex\(\(item\) => item\.key === step\) < 6/);
  assertSourceMatch(storyboardGallery, /<OnboardingJourneyView step=\{step\} topInsetReduction=\{topInsetReductionForOnboardingStoryboard\(step\)\} \/>/);
  assertSourceMatch(storyboardGallery, /<SubscriptionPreviewContent context="onboarding" topInsetReduction=\{topInsetReductionForOnboardingStoryboard\(step\)\} \/>/);
  assertSourceMatch(onboardingPreview, /presentationPropsForOnboardingStep\(step as OnboardingJourneyStep\)/);
  assertSourceMatch(onboardingPreview, /\{\.\.\.presentationProps\}/);
  assertSourceMatch(journey, /usesRefinedPresentation = index >= 1/);
  assertSourceMatch(journey, /fixedProfileChrome: index >= 7 && index <= 12/);
  assertSourceMatch(journey, /profileQuestionSpacing: index >= 7 && index <= 12 \? 24 : 0/);
  assertSourceMatch(journey, /fullWidthExplanationTransition: index >= 1 && index <= 5/);
  assertSourceMatch(journey, /profileProgressEyebrowBottomSpacing: index >= 7 && index <= 12 \? 18 : 0/);
  assertSourceMatch(journey, /profileEyebrowsMuted: usesRefinedPresentation/);
  assertSourceMatch(journey, /hideCalculationReviewDisclosure: usesRefinedPresentation/);
  assertSourceMatch(journey, /progressiveAllergyDetails: usesRefinedPresentation/);
  assertSourceMatch(journey, /storyboardSummaryLayout: usesRefinedPresentation/);
  assertSourceMatch(journey, /contentSizedDietaryChips: usesRefinedPresentation/);
  assertSourceMatch(journey, /conciseSexEyebrow: usesRefinedPresentation/);
  assertSourceMatch(journey, /measurementReferenceNotice: usesRefinedPresentation/);
  assertSourceMatch(journey, /measurementReferenceNotice \? <InlineNotice>El peso inicial quedará como primera referencia de tu evolución\.<\/InlineNotice>/);
  assertSourceMatch(journey, /conciseSexEyebrow \? "Sexo" : "Sexo usado para el cálculo nutricional"/);
  assertSourceMatch(journey, /dietaryChoiceGridCentered: \{ justifyContent: "center" \}/);
  assertSourceMatch(journey, /dietaryChoiceChipContentSized: \{ flexBasis: "auto", flexGrow: 0, paddingHorizontal: tokens\.spacing\.xl \}/);
  assertSourceMatch(journey, /controller\.values\.allergy === "otra"/);
  assertSourceMatch(journey, /placeholder=\{progressiveAllergyDetails \? "Indícanos tu condición relevante"/);
  assertSourceMatch(journey, /profileProgressBottomSpacing: index >= 7 && index <= 12 \? 24 : 0/);
  assertSourceMatch(journey, /profileProgressWidthReduction: index >= 7 && index <= 12 \? 36 : 0/);
  assertSourceMatch(journey, /profileTitleBottomSpacingReduction: index >= 7 && index <= 12 \? 12 : 0/);
  assertSourceMatch(journey, /showGoalOptionsEyebrow: usesRefinedPresentation/);
  assertSourceMatch(journey, /showProfileControlBleed: usesRefinedPresentation/);
  assertSourceMatch(journey, /fixedProfileChrome: index >= 7 && index <= 12/);
  assertSourceMatch(journey, /disclosuresTitleSpacingReduction: index === 6 \? 18 : 0/);
  assertSourceMatch(journey, /fixedDisclosuresFooter: index === 6/);
  assertSourceMatch(journey, /fixedProfileFooterBottomSpacing: index >= 7 && index <= 12 \? 46 : 0/);
  assertSourceDoesNotMatch(onboardingPreview, /fixedLoginActionBottomSpacing=\{134\}/);
  assert.ok(journey.includes("fixedLoginActionBottomSpacing: 0"));
  assertSourceMatch(onboardingPreview, /scroll=\{usesFixedDisclosuresFooter \|\| usesFixedProfileChrome \? false : stepIndex >= 6 \? "auto" : false\}/);
  assertSourceMatch(journey, /marginBottom: profileProgressEyebrowBottomSpacing/);
  assertSourceMatch(journey, /marginBottom: profileProgressBottomSpacing/);
  assertSourceMatch(journey, /paddingHorizontal: tokens\.spacing\.xl \+ \(profileProgressWidthReduction \/ 2\)/);
  assertSourceMatch(journey, /scrollEnabled=\{contentOverflows\}/);
  assertSourceMatch(journey, /const contentOverflows = contentHeight > viewportHeight \+ 1/);
  assertSourceMatch(journey, /fixedProfileScroll: \{ flex: 1, marginHorizontal: -tokens\.spacing\.screen \}/);
  assertSourceMatch(journey, /fixedProfileScrollContent: \{[^}]*paddingHorizontal: tokens\.spacing\.screen/);
  assertSourceMatch(journey, /marginBottom: fixedProfileFooterBottomSpacing/);
  assertSourceMatch(journey, /<Text style=\{profileQuestionStyle\}>MI OBJETIVO<\/Text>/);
  assertSourceMatch(journey, /profileControlBleed: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  assertSourceMatch(journey, /marginTop: styles\.centeredTitleSpacing\.marginTop - disclosuresTitleSpacingReduction/);
  assertSourceMatch(journey, /function DisclosuresStepLayout/);
  assertSourceMatch(journey, /profileQuestionSpacing > 0 && \{ gap: profileQuestionSpacing \}/);
  assertSourceMatch(journey, /profileQuestionMuted: \{ color: tokens\.color\.textMuted \}/);
  assertSourceMatch(journey, /fullWidthExplanationViewport: \{[^}]*marginHorizontal: -tokens\.spacing\.screen/);
  assertSourceMatch(journey, /fullWidthExplanationSlide: \{ paddingHorizontal: tokens\.spacing\.screen \}/);
});

test("the label capture gallery exposes the complete happy-path storyboard without product side effects", async () => {
  const gallery = await readTestFile(path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"), "utf8");
  const navigation = await readTestFile(path.resolve(process.cwd(), "src/components/dev/gallery-navigation.tsx"), "utf8");
  const storyboardGallery = await readTestFile(path.resolve(process.cwd(), "src/components/dev/storyboard-gallery.tsx"), "utf8");
  const storyboard = await readTestFile(path.resolve(process.cwd(), "src/components/label-capture/label-capture-storyboard.tsx"), "utf8");
  const scanBeam = await readTestFile(path.resolve(process.cwd(), "src/components/label-capture/animated-scan-beam.tsx"), "utf8");

  assertSourceMatch(navigation, /\{ key: "labelCapture", label: "Etiquetas" \}/);
  assertSourceMatch(gallery, /<LabelCaptureStoryboardGallery \/>/);
  assertSourceMatch(storyboardGallery, /accessibilityLabel="Formatos de la digitalización de etiquetas"/);
  assertSourceMatch(storyboardGallery, /steps=\{labelCaptureStoryboardSteps\}/);
  for (const step of ["intro", "camera", "preview", "processing", "review", "confirmation", "saved"]) {
    assertSourceMatch(storyboard, new RegExp(`key: "${step}"`));
  }
  assertSourceMatch(storyboard, /datos fijos|Yogur griego natural/);
  assertSourceMatch(storyboard, /Validamos nitidez antes de usar créditos/);
  assertSourceMatch(storyboard, /Confirmar y crear alimento/);
  assertSourceMatch(storyboard, /<AnimatedScanBeam gradientId="label-capture-credit-scan" \/>/);
  assertSourceMatch(scanBeam, /Animated\.loop\(Animated\.sequence/);
  assertSourceMatch(scanBeam, /toValue: 1[\s\S]*toValue: 0/);
  assertSourceMatch(scanBeam, /outputRange: \[0, Math\.max\(0, height - beamHeight\)\]/);
  assertSourceMatch(scanBeam, /beam: \{ height: beamHeight, left: 0[\s\S]*right: 0, top: 0/);
  assertSourceMatch(storyboard, /nutritionLabel: \{ color: tokens\.color\.textMain/);
  assertSourceMatch(storyboard, /nutritionLabelEmphasis: \{ fontWeight: tokens\.weight\.bold \}/);
  assertSourceMatch(storyboard, /<DistributedTabBar<"g" \| "ml">/);
  assertSourceMatch(storyboard, /tabs=\{\[\{ key: "g", label: "Gramos" \}, \{ key: "ml", label: "Mililitros" \}\]\}/);
  assertSourceMatch(storyboard, /<DistributedTabBar<"g" \| "ml">[\s\S]*bleed/);
  const proteinIndex = storyboard.indexOf('{ emphasized: true, label: "Proteínas"');
  const fatIndex = storyboard.indexOf('{ emphasized: true, label: "Grasas totales"');
  const saturatedFatIndex = storyboard.indexOf('{ label: "Grasas saturadas"');
  const carbsIndex = storyboard.indexOf('{ emphasized: true, label: "Carbohidratos"');
  const sugarIndex = storyboard.indexOf('{ label: "Azúcares"');
  const fiberIndex = storyboard.indexOf('{ label: "Fibra"');
  const sodiumIndex = storyboard.indexOf('{ label: "Sodio"');
  assert.ok(proteinIndex < fatIndex && fatIndex < saturatedFatIndex && saturatedFatIndex < carbsIndex && carbsIndex < sugarIndex && sugarIndex < fiberIndex && fiberIndex < sodiumIndex);
  assertSourceMatch(storyboard, /intro: \{ leading: "back", trailing: null \}/);
  assertSourceDoesNotMatch(storyboard, /leading: "menu"|PanelRight/);
  assertSourceDoesNotMatch(storyboard, /apiRequest|expo-camera|useCameraPermissions|useSession/);
});

test("the committed mobile contract exposes every route consumed through CML08", async () => {
  const file = path.resolve(process.cwd(), "../docs/00_current/api/mobile-v1.openapi.json");
  const schema = JSON.parse(await readTestFile(file, "utf8")) as { info: { version: string }; paths: Record<string, unknown> };
  assert.equal(schema.info.version, "1.0.0");
  for (const route of [
    "/api/v1/session",
    "/api/v1/sessions/{device_session_id}",
    "/api/v1/me",
    "/api/v1/onboarding",
    "/api/v1/today",
    "/api/v1/today/pinned-plan",
    "/api/v1/today/pinned-plan/meals/{meal_key}/check-ins",
    "/api/v1/program/active",
    "/api/v1/program/calendarizations",
    "/api/v1/program/calendarizations/history",
    "/api/v1/program/calendarizations/{calendarization_id}/pause",
    "/api/v1/program/calendarizations/{calendarization_id}/resume",
    "/api/v1/program/calendarizations/{calendarization_id}/cancel",
    "/api/v1/program/days/{day_id}",
    "/api/v1/proposals",
    "/api/v1/proposals/{proposal_id}",
    "/api/v1/proposals/{proposal_id}/approve",
    "/api/v1/proposals/{proposal_id}/reject",
    "/api/v1/proposals/{proposal_id}/cancel",
    "/api/v1/proposals/{proposal_id}/apply",
    "/api/v1/comparisons/metadata",
    "/api/v1/comparisons/options/{kind}",
    "/api/v1/comparisons/compare",
    "/api/v1/comparisons/saved",
    "/api/v1/comparisons/saved/{comparison_id}",
    "/api/v1/ai/chats",
    "/api/v1/ai/chats/{chat_id}",
    "/api/v1/ai/turns",
    "/api/v1/ai/jobs/{job_id}",
    "/api/v1/ai/prepared-actions/{action_id}/commit",
    "/api/v1/ai/prepared-actions/{action_id}/cancel",
    "/api/v1/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
    "/api/v1/program/active/reminders",
    "/api/v1/notifications/apple/device",
    "/api/v1/program/reviews",
    "/api/v1/program/revisions",
    "/api/v1/program/revisions/{revision_id}/decision",
    "/api/v1/weights",
    "/api/v1/library/programs",
    "/api/v1/library/daily-plans",
    "/api/v1/library/meals",
    "/api/v1/library/foods",
    "/api/v1/library/meals/{meal_id}/food-picker/preview",
    "/api/v1/library/meals/{meal_id}/food-picker/commit",
    "/api/v1/library/daily-plans/{dailyplan_id}/meal-picker/preview",
    "/api/v1/library/daily-plans/{dailyplan_id}/meal-picker/commit",
    "/api/v1/library/programs/{program_id}/daily-plan-picker/preview",
    "/api/v1/library/programs/{program_id}/daily-plan-picker/commit",
    "/api/v1/food-picker-options/{food_id}",
    "/api/v1/library/programs/{program_id}/week-picker/preview",
    "/api/v1/library/programs/{program_id}/week-picker/commit",
    "/api/v1/foods/label-captures",
    "/api/v1/foods/label-captures/config",
    "/api/v1/foods/label-captures/analyze",
    "/api/v1/foods/label-captures/{receipt_id}/image",
    "/api/v1/subscriptions",
    "/api/v1/subscriptions/apple/transactions",
    "/api/v1/account/disclosures",
    "/api/v1/account/delete",
  ]) {
    assert.ok(schema.paths[route], `missing ${route}`);
  }
});

test("composition picker previews expose complete projected entities and relation replacement", async () => {
  const file = path.resolve(process.cwd(), "../docs/00_current/api/mobile-v1.openapi.json");
  const schema = JSON.parse(await readTestFile(file, "utf8")) as {
    components: { schemas: Record<string, { properties?: Record<string, unknown> }> };
  };
  const schemas = schema.components.schemas;
  assert.ok(schemas.FoodPickerInput.properties?.meal_food_id);
  assert.ok(schemas.PickerPreviewData.properties?.result);
  for (const property of ["entity", "name", "nutrition", "indicators", "panel"]) {
    assert.ok(schemas.PickerResultData.properties?.[property], `missing picker result ${property}`);
  }
  for (const itemSchema of ["LibraryFoodPanelItemData", "LibraryMealPanelItemData", "LibraryWeekDayData"]) {
    assert.ok(schemas[itemSchema].properties?.is_projected, `missing ${itemSchema}.is_projected`);
    assert.ok(schemas[itemSchema].properties?.projected_label, `missing ${itemSchema}.projected_label`);
  }
});

test("the App Store review package is complete, bounded and secret-free", async () => {
  const store = path.resolve(process.cwd(), "store");
  const metadata = JSON.parse(await readTestFile(path.join(store, "metadata/es-CL.json"), "utf8"));
  const privacy = JSON.parse(await readTestFile(path.join(store, "privacy-labels.json"), "utf8"));
  const screenshots = JSON.parse(await readTestFile(path.join(store, "screenshots/manifest.json"), "utf8"));
  const notes = await readTestFile(path.join(store, "review-notes.es-CL.md"), "utf8");

  assert.ok(metadata.name.length <= 30);
  assert.ok(metadata.subtitle.length <= 30);
  assert.ok(Buffer.byteLength(metadata.keywords, "utf8") <= 100);
  assertSourceMatch(metadata.privacy_policy_url, /^https:\/\//);
  assertSourceMatch(metadata.support_url, /^https:\/\//);
  assert.equal(privacy.tracking, false);
  assert.equal(screenshots.shots.length, 5);
  assert.ok(screenshots.shots.every((shot: { route: string }) => shot.route !== "/check-in"));
  assertSourceMatch(notes, /App Store Connect/);
  assertSourceDoesNotMatch(notes, /check-in del día/i);
  assertSourceDoesNotMatch(notes, /password\s*[=:]\s*\S+/i);
});

test("the iOS release contract declares only approved capabilities and privacy categories", async () => {
  const appFile = path.resolve(process.cwd(), "app.json");
  const app = JSON.parse(await readTestFile(appFile, "utf8")).expo as {
    ios: { associatedDomains: string[]; usesAppleSignIn: boolean; privacyManifests: { NSPrivacyTracking: boolean; NSPrivacyCollectedDataTypes: { NSPrivacyCollectedDataType: string }[] } };
    android: { intentFilters: { autoVerify: boolean; data: { host: string; pathPrefix: string; scheme: string }[] }[] };
    plugins: (string | [string, Record<string, unknown>])[];
  };
  assert.equal(app.ios.usesAppleSignIn, true);
  assert.equal(app.ios.privacyManifests.NSPrivacyTracking, false);
  assert.deepEqual(app.ios.associatedDomains, ["applinks:www.myscoope.com"]);
  assert.equal(app.android.intentFilters[0].autoVerify, true);
  assert.deepEqual(app.android.intentFilters[0].data, [
    { scheme: "https", host: "www.myscoope.com", pathPrefix: "/s/" },
  ]);
  const collected = new Set(
    app.ios.privacyManifests.NSPrivacyCollectedDataTypes.map((item) => item.NSPrivacyCollectedDataType),
  );
  for (const category of [
    "NSPrivacyCollectedDataTypeHealth",
    "NSPrivacyCollectedDataTypeFitness",
    "NSPrivacyCollectedDataTypeDeviceID",
    "NSPrivacyCollectedDataTypeCrashData",
  ]) assert.ok(collected.has(category), `missing ${category}`);

  const secureStore = app.plugins.find((plugin) => Array.isArray(plugin) && plugin[0] === "expo-secure-store");
  const camera = app.plugins.find((plugin) => Array.isArray(plugin) && plugin[0] === "expo-camera");
  assert.deepEqual(secureStore, ["expo-secure-store", { configureAndroidBackup: true, faceIDPermission: false }]);
  assert.equal(Array.isArray(camera) && camera[1].microphonePermission, false);
  assert.equal(Array.isArray(camera) && camera[1].barcodeScannerEnabled, false);
});

test("recoverable API failures have bounded product messages", () => {
  const expected = new Map([
    [403, "permiso"],
    [404, "disponible"],
    [409, "cambió"],
    [422, "validar"],
    [429, "varias solicitudes"],
    [503, "disponible"],
  ]);
  for (const [status, fragment] of expected) {
    const message = userFacingError(new MobileApiError("raw provider detail", "unmapped", status));
    assertSourceMatch(message, new RegExp(fragment, "i"));
    assertSourceDoesNotMatch(message, /raw provider detail/);
  }
  assertSourceMatch(userFacingError(new MobileApiError("failed", "assistant_turn_failed", 422)), /conversación anterior sigue guardada/i);
});
