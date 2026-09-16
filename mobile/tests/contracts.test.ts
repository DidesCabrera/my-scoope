import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { MobileApiError, userFacingError } from "../src/api/errors";
import { tokens } from "../src/generated/ui-tokens";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("mobile visual grammar exposes the reusable card and nutrition tokens", () => {
  assert.equal(tokens.contract, "myscoope.visual-grammar.v2");
  assert.equal(tokens.radius.card, 22);
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
});

test("the development UI gallery remains available at /dev/ui-gallery", async () => {
  const gallery = await readTestFile(
    path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"),
    "utf8",
  );
  assertSourceMatch(gallery, /export default function UiGalleryScreen/);
  assertSourceMatch(gallery, /if \(!__DEV__\) return <Redirect href="\/" \/>/);
  assertSourceMatch(gallery, /Galería del sistema UI/);
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
  assertSourceDoesNotMatch(nutritionKpi, /density\?: "compact" \| "regular"/);
  assertSourceDoesNotMatch(nutritionKpi, /height: compact \? "100%"/);

  const libraryCard = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryCard, /NutritionEntityCard.*from "@\/components\/nutrition"/);
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
    ["src/app/comparator/index.tsx", "comparator", "Comparador"],
    ["src/app/assistant/index.tsx", "chat", "Asistente AI"],
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

  const menuPanelSource = await readTestFile(
    path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(menuPanelSource, /menuFoods: \{ color: tokens\.color\.textMain/);
  assertSourceDoesNotMatch(menuPanelSource, /menuFoods: \{[^}]*opacity:/);

  const libraryEntityPanels = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryEntityPanels, /perKilogram: item\.protein_per_kilogram/);
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
  assertSourceDoesNotMatch(programWeekPanels, /cell: \{[^}]*fontSize: 11/);
  assertSourceDoesNotMatch(programWeekPanels, /<PanelAllocationBar size="compact"/);
  assertSourceMatch(programWeekPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assertSourceDoesNotMatch(programWeekPanels, /deltaUp|deltaDown|styles\.(?:protein|carbs|fat)(?:[,}\]])/);
  assertSourceMatch(programWeekPanels, /Header columns=\{\[\{ key: "ppk", label: "PpK" \}, \{ key: "protein", label: "P g" \}, \{ key: "carbs", label: "C g" \}, \{ key: "fat", label: "F g" \}\]\}/);
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
  assertSourceMatch(programDetail, /<FoodPanels items=\{weekData/);
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
  assertSourceMatch(calendarizedPlanning, /<SectionDivider spacing="compact" tone="soft" \/>/);
  assertSourceMatch(calendarizedPlanning, /title="Alimentos en esta semana"/);
  assertSourceMatch(calendarizedPlanning, /<FoodPanels items=\{weekFoods\} onOpenItem=/);

  const calendarizedDailyPlanCard = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-daily-plan-card.tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedDailyPlanCard, /<NutritionEntityCard/);
  assertSourceMatch(calendarizedDailyPlanCard, /beforeNutrition=\{<DailyMealCompletionCard mealExecution=\{mealExecution\} mealKeys=\{meals\.map\(\(meal\) => meal\.key\)\} \/>\}/);
  assertSourceMatch(calendarizedDailyPlanCard, /<MealPanels/);
  assertSourceMatch(calendarizedDailyPlanCard, /onOpenItem=/);
  assertSourceMatch(calendarizedDailyPlanCard, /pathname: "\/program\/days\/\[id\]\/meals\/\[mealKey\]"/);
  assertSourceMatch(calendarizedDailyPlanCard, /mealKey: meal\.id/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /kpiVariant="nested"/);
  assertSourceMatch(calendarizedDailyPlanCard, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assertSourceDoesNotMatch(calendarizedDailyPlanCard, /completedCount: executions\.filter/);
  assertSourceMatch(calendarizedDailyPlanCard, /noteCount: executions\.filter/);
  assertSourceMatch(calendarizedDailyPlanCard, /label: "posición", value: `S\$\{position\.weekNumber\} · D\$\{position\.dayNumber\}`/);

  const calendarizedMealDetail = await readTestFile(
    path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"),
    "utf8",
  );
  assertSourceMatch(calendarizedMealDetail, /apiRequest<CalendarizedDayDetail>\(`\/api\/v1\/program\/days\/\$\{dayId\}`\)/);
  assertSourceMatch(calendarizedMealDetail, /day\.plan_snapshot\?\.meals\?\.find/);
  assertSourceMatch(calendarizedMealDetail, /beforeNutrition=\{<MealCompletionCard controller=\{adherence\} \/>\}/);
  assertSourceMatch(calendarizedMealDetail, /<FoodPanels\s+editing=\{\{/);
  assertSourceMatch(calendarizedMealDetail, /ordered_keys: items\.map\(\(item\) => item\.id\)/);
  assertSourceMatch(calendarizedMealDetail, /relationKey: food\.id/);
  assertSourceMatch(calendarizedMealDetail, /onEditPortion:/);
  assertSourceMatch(calendarizedMealDetail, /<MealNoteCard controller=\{adherence\} \/>/);
  assertSourceMatch(calendarizedMealDetail, /completion=\{\{/);
  assertSourceMatch(calendarizedMealDetail, /onChange: setExecution/);
  assertSourceMatch(calendarizedMealDetail, /secondaryAction: meal \? \{ icon: "clock", label: "Cambiar hora"/);
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
  assertSourceMatch(sharedEntityPanels, /menuRow: \{[^}]*paddingVertical: tokens\.spacing\.lg/);
  assertSourceMatch(sharedEntityPanels, /menuCopy: \{ flex: 1, gap: tokens\.spacing\.sm/);
  assertSourceMatch(sharedEntityPanels, /menuAction: \{[^}]*minWidth: 24/);
  assertSourceMatch(sharedEntityPanels, /<MealRowIdentity completed=\{item\.completed\} menu name=\{item\.name\} projectedLabel=\{item\.projectedLabel\} \/>[\s\S]*item\.time \? \([\s\S]*<Clock color=\{tokens\.color\.textMuted\} size=\{11\} strokeWidth=\{2\} \/>[\s\S]*<Text style=\{styles\.menuTime\}>\{item\.time\}<\/Text>/);
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
  assertSourceMatch(mealAdherence, /onToggle\(!completed\)/);
  assertSourceMatch(mealAdherence, /export function MealNoteCard/);
  assertSourceDoesNotMatch(mealAdherence, /Marca la casilla si cumpliste esta comida del programa/);
  assertSourceMatch(mealAdherence, /<MealCompletionSurface>/);
  assertSourceMatch(mealAdherence, /checkbox: \{[^}]*borderRadius: tokens\.radius\.pill/);
  assertSourceMatch(mealAdherence, /completionLabel: \{[^}]*fontSize: tokens\.type\.caption/);
  assertSourceMatch(mealAdherence, /<SectionHeading title="Nota de esta comida" \/>/);
  assertSourceMatch(mealAdherence, /controller\.editingNote \? <TextInput[\s\S]*styles\.noteText/);
  assertSourceDoesNotMatch(mealAdherence, /styles\.divider/);

  assertSourceMatch(sharedEntityPanels, /preparationMarkerChecked/);
  assertSourceMatch(sharedEntityPanels, /preparation\.isPrepared\(item\) \? <View style=\{styles\.preparationMarkerChecked\} \/> : null/);
  assertSourceMatch(sharedEntityPanels, /preparationMarker: \{[^}]*borderColor: tokens\.color\.borderDefault/);
  assertSourceMatch(sharedEntityPanels, /preparationMarkerChecked: \{ backgroundColor: tokens\.color\.food, borderRadius: 5, height: 10, width: 10 \}/);
  assertSourceMatch(sharedEntityPanels, /accessibilityRole="checkbox"/);
  assertSourceMatch(sharedEntityPanels, /<PanelHeaderCell \{\.\.\.sorting\} sortKey="prepared" style=\{styles\.preparationValue\}>Listo<\/PanelHeaderCell>/);
  assertSourceDoesNotMatch(mealAdherence, /statusLabel|styles\.status/);
  assertSourceDoesNotMatch(mealAdherence, /Cumplimiento actualizado|Nota guardada|statusSaved|noteSaved/);
  assertSourceDoesNotMatch(mealAdherence, /label=\{editingNote \? "Guardar nota" : "Editar nota"\}/);

  const mealCompletionSummary = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/meal-completion-summary.tsx"),
    "utf8",
  );
  assertSourceMatch(mealCompletionSummary, /Cumplimiento comidas/);
  assertSourceMatch(mealCompletionSummary, /label: \{[^}]*fontSize: tokens\.type\.caption/);
  assertSourceMatch(mealCompletionSummary, /item\.status === "completed"/);
  assertSourceMatch(mealCompletionSummary, /checkCircleCompleted: \{ backgroundColor: tokens\.color\.meal \}/);
  assertSourceMatch(mealCompletionSummary, /checkCirclePending: \{ backgroundColor: tokens\.color\.borderDefault \}/);
  assertSourceMatch(mealCompletionSummary, /completed \? tokens\.color\.entityIconForeground : tokens\.color\.textMuted/);
  assertSourceMatch(mealCompletionSummary, /surface: \{ backgroundColor: `\$\{tokens\.color\.meal\}1A`, borderColor: tokens\.color\.meal, borderRadius: tokens\.radius\.lg, borderWidth: 1/);
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
  assertSourceMatch(activeProgram, /<SectionDivider \/>[\s\S]*<SectionHeading[^>]*title="Planificación Semanal"/);
  assertSourceMatch(activeProgram, /<ProgramActiveOverview[\s\S]*<DetailLinkRow[\s\S]*<SectionDivider \/>[\s\S]*<SectionHeading[^>]*title="Planificación Semanal"/);
  assertSourceMatch(activeProgram, /label="Ver plantilla original"/);
  assertSourceMatch(activeProgram, /conserva lo que realmente ocurrió/);
  assertSourceMatch(activeProgram, /weekCount === 1 \? "semana" : "semanas"/);

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
  assertSourceDoesNotMatch(activeProgramOverview, /<ProgramActiveKpis[^>]*bleed=\{false\}/);
  assertSourceMatch(activeProgramOverview, /eyebrow="Programa activo"/);
  assertSourceDoesNotMatch(activeProgramOverview, /eyebrow="Programa en curso"/);
  assertSourceMatch(activeProgramOverview, /SectionHeading icon=\{<Activity[^>]*>\} title="Métricas de activación"/);
  assertSourceMatch(activeProgramOverview, /embedded \? <DetailLinkRow[\s\S]*router\.push\("\/program" as Href\)/);
  assertSourceMatch(activeProgramOverview, /activeIndicators = program\.indicators\.map/);
  assertSourceMatch(activeProgramOverview, /indicator\.icon === "week"[\s\S]*?icon: undefined[\s\S]*?Number\(indicator\.value\) === 1 \? "SEMANA" : "SEMANAS"/);
  assertSourceMatch(activeProgramOverview, /indicators=\{\[\.\.\.\(embedded \? \[\] : activeIndicators\), \{ icon: "week", iconPosition: "leading", label: "periodo", tone: "surfaceMuted"/);
  assertSourceMatch(activeProgramOverview, /value: `\$\{compactDateLabel\(calendarization\.start_date\)\} — \$\{compactDateLabel\(calendarization\.end_date\)\}`/);
  assertSourceMatch(activeProgramOverview, /export function ProgramActiveHomeOverview[\s\S]*<ProgramActiveOverview \{\.\.\.props\} embedded/);
  assertSourceMatch(activeProgramOverview, /embedded[\s\S]*<Card accent=\{tokens\.color\.program\} style=\{styles\.content\}>\{content\}<\/Card>/);

  const activeProgramKpis = await readTestFile(
    path.resolve(process.cwd(), "src/components/programs/program-active-kpis.tsx"),
    "utf8",
  );
  assertSourceDoesNotMatch(activeProgramKpis, /periodRow|periodDates|CalendarDays/);
  assertSourceDoesNotMatch(activeProgramKpis, /kcalSurface|kcalBorder|periodBorder|periodText/);
  assertSourceMatch(activeProgramKpis, /indicatorsSurfaceReset:\{[^}]*padding:tokens\.spacing\.xs/);
  assertSourceMatch(activeProgramKpis, /Días recorridos/);
  assertSourceMatch(activeProgramKpis, /indicator:\{[^}]*padding:tokens\.spacing\.md/);
  assertSourceMatch(activeProgramKpis, /indicatorValue:\{[^}]*marginTop:tokens\.spacing\.sm/);
  assertSourceMatch(activeProgramKpis, /fraction:\{[^}]*fontSize:tokens\.type\.section/);
  assertSourceMatch(activeProgramKpis, /percentageText:\{[^}]*fontSize:tokens\.type\.section/);
  assertSourceMatch(activeProgramKpis, /percentageText:\{[^}]*color:tokens\.color\.textMain/);
  assertSourceMatch(activeProgramKpis, /<Text style=\{styles\.percentageText\}>\{advancement\}%<\/Text>/);
  assertSourceMatch(activeProgramKpis, /<Text style=\{styles\.percentageText\}>\{compliance\}%<\/Text>/);
  assertSourceMatch(activeProgramKpis, /indicatorElapsed:\{backgroundColor:`\$\{tokens\.color\.dailyPlan\}1A`,borderColor:tokens\.color\.dailyPlan\}/);
  assertSourceMatch(activeProgramKpis, /indicatorAdherence:\{backgroundColor:`\$\{tokens\.color\.meal\}1A`,borderColor:tokens\.color\.meal\}/);
  assertSourceDoesNotMatch(activeProgramKpis, /percentageTag/);

  const activateProgram = await readTestFile(
    path.resolve(process.cwd(), "src/app/program/activate.tsx"),
    "utf8",
  );
  assertSourceMatch(activateProgram, /stickyHeaderIndices=\{\[0\]\}/);
  assertSourceMatch(activateProgram, /<PickerEntryTabs[\s\S]*createLabel="Crear Nuevo"/);
  assertSourceMatch(activateProgram, /accessibilityLabel="Buscar programa"/);
  assertSourceMatch(activateProgram, /pathname: "\/libraries\/create", params: \{ entity: "program" \}/);
  assertSourceMatch(activateProgram, /<ProgramChildCard[\s\S]*openActionLabel="Seleccionar"/);
  assertSourceMatch(activateProgram, /<ProgramChildCard[\s\S]*openActionLabel="Cambiar selección"/);
  assertSourceMatch(activateProgram, /<SectionHeading title="Configura la selección" \/>/);
  assertSourceMatch(activateProgram, /label="Calendarizar programa"/);
  assertSourceDoesNotMatch(activateProgram, /PASO 3 DE 3|Confirma la calendarización|Volver a configurar/);

  const todayScreen = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  assertSourceMatch(todayScreen, /<AppHeader[\s\S]*?title=\{`Vamos, \$\{firstName\}`\}[\s\S]*?\/>[\s\S]*<CurrentWeekSection localDate=\{today\.local_date\} \/>/);
  assertSourceDoesNotMatch(todayScreen, /<AppHeader eyebrow=/);
  assert.ok(todayScreen.indexOf("<CurrentWeekSection") < todayScreen.indexOf("<CalendarizedDailyPlanCard"));
  assertSourceMatch(todayScreen, /<CurrentWeekSection[\s\S]*?<HomeSectionTitle>\{`Tu Plan para hoy, \$\{homePlanDateLabel\(today\.local_date\)\}`\}<\/HomeSectionTitle>[\s\S]*?<CalendarizedDailyPlanCard/);
  assert.ok(todayScreen.indexOf("<CalendarizedDailyPlanCard") < todayScreen.indexOf("<ProgramActiveHomeOverview"));
  assertSourceMatch(todayScreen, /<CalendarizedDailyPlanCard[\s\S]*?<HomeSectionTitle>Tu Programa Activo<\/HomeSectionTitle>[\s\S]*?<ProgramActiveHomeOverview/);
  assertSourceMatch(todayScreen, /homeSectionTitle: \{[^}]*fontSize: 18[^}]*marginBottom: -tokens\.spacing\.sm[^}]*marginTop: tokens\.spacing\.sm/);
  assertSourceDoesNotMatch(todayScreen, /<SectionDivider \/>/);
  const currentWeek = await readTestFile(
    path.resolve(process.cwd(), "src/components/calendarization/current-week-section.tsx"),
    "utf8",
  );
  assertSourceDoesNotMatch(currentWeek, /Semana en curso|<SectionHeading/);
  assertSourceMatch(currentWeek, /<Text[^>]*styles\.monthLabel[^>]*>\{day\.monthLabel\}<\/Text>/);
  assertSourceMatch(currentWeek, /dayCircle: \{[^}]*backgroundColor: tokens\.color\.surfaceCard[^}]*height: 44[^}]*width: 44/);
  assertSourceMatch(currentWeek, /monthLabel: \{[^}]*fontFamily: font\.regular[^}]*fontSize: 9[^}]*fontWeight: "300"[^}]*lineHeight: 10/);
  assertSourceMatch(currentWeek, /monthLabelToday: \{ color: tokens\.color\.surfaceApp, fontWeight: tokens\.weight\.regular \}/);
  assertSourceMatch(currentWeek, /<WeekDaySelectionRing \/>/);
  assertSourceMatch(currentWeek, /dayCircleToday: \{ backgroundColor: tokens\.color\.entityIconForeground \}/);
  assertSourceMatch(currentWeek, /dayNumberToday: \{ color: tokens\.color\.surfaceApp \}/);
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
  assertSourceMatch(weekDayGrid, /stopColor="#D62976"/);
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
  assertSourceMatch(todayScreen, /alignment="center"/);
  assertSourceMatch(todayScreen, /<GuideMetric icon="weight" tone="ppk" value=\{`\$\{displayWeight\(currentWeightKg\)\} kg`\} \/>/);
  assertSourceDoesNotMatch(todayScreen, /GuideMetric label="Peso actual"/);
  assertSourceMatch(productUiSourceForIndicators, /guideMetricValueOnly: \{ borderRadius: tokens\.radius\.lg, minHeight: 40 \}/);
  assertSourceMatch(productUiSourceForIndicators, /guideMetricPpk: \{ backgroundColor: `\$\{tokens\.color\.ppk\}1A`, borderColor: tokens\.color\.ppk, borderWidth: 1 \}/);
  assertSourceMatch(todayScreen, /apiRequest<WeightListData>\("\/api\/v1\/weights\?limit=1"\)/);
  assertSourceMatch(todayScreen, /latestWeightKg \?\? profile\?\.current_weight_kg \?\? today\?\.measurements\?\.latest_weight_kg/);
  assertSourceMatch(todayScreen, /displayWeight\(currentWeightKg\)/);
  assertSourceMatch(todayScreen, /dateLabel=\{compactDateLabel\(today\.local_date\)\}/);
  assertSourceMatch(todayScreen, /<HomeLibraryGrid counts=\{libraryCounts\} \/>/);
  assertSourceMatch(todayScreen, /\/api\/v1\/library\/programs\?limit=1/);
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
  assertSourceMatch(homeLibraryGrid, /section: \{[^}]*marginHorizontal: -tokens\.spacing\.screen/);
  assertSourceMatch(homeLibraryGrid, /<SectionDivider spacing="compact" style=\{styles\.sectionDivider\} \/>/);
  assertSourceMatch(homeLibraryGrid, /sectionDivider: \{ marginHorizontal: 0 \}/);
  assertSourceMatch(homeLibraryGrid, /padding: tokens\.card\.outerPadding/);
  assertSourceMatch(homeLibraryGrid, /borderTopColor: tokens\.color\[entry\.entity\]/);
  assertSourceMatch(homeLibraryGrid, /borderTopWidth: 3/);
  assertSourceMatch(homeLibraryGrid, /title: \{[^}]*fontSize: tokens\.type\.body/);
  assertSourceDoesNotMatch(homeLibraryGrid, /description:/);
  assertSourceDoesNotMatch(todayScreen, /<ProgramActiveCard/);
  assertSourceMatch(todayScreen, /activeProgram\?\.days\.find\(\(day\) => day\.id === today\?\.day_id\)/);
  assertSourceMatch(todayScreen, /position=\{todayProgramDay \? \{ dayNumber: todayProgramDay\.day_number, weekNumber: todayProgramDay\.week_number \} : undefined\}/);
  assertSourceDoesNotMatch(activeProgram, /program\?\.days\.map/);

  const libraryDetail = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"),
    "utf8",
  );
  assertSourceMatch(libraryDetail, /<ProgramDetailPreview[\s\S]*?scrollable\s*\/>/);
  assertSourceMatch(libraryDetail, /FoodPanels, MealPanels.*from "@\/components\/panels"/);
  assertSourceMatch(libraryDetail, /title="Alimentos en este plan diario"><FoodPanels items=\{item\.panel\.foods\.map\(foodPanelItem\)\}/);
  assertSourceMatch(libraryDetail, /<SectionDivider \/><EntityDetailSection[^>]*title="Detalle de cada Comida"/);
  assertSourceMatch(libraryDetail, /<SectionDivider \/><EntityDetailSection[^>]*title="Alimentos en este plan diario"/);
  assertSourceMatch(libraryDetail, /hasMealTimeContext[\s\S]*?\? \{ icon: "clock", label: "Cambiar hora"/);
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
  assertSourceMatch(calendarizedDayDetail, /<FoodPanels items=\{foods\} onOpenItem=/);
  assertSourceMatch(calendarizedDayDetail, /<MealPanels\s+editing=\{\{/);
  assertSourceMatch(calendarizedDayDetail, /relationKey: meal\.id/);
  assertSourceMatch(calendarizedDayDetail, /\/meals\/order/);
  assertSourceMatch(calendarizedDayDetail, /beforeNutrition=\{<DailyMealCompletionCard mealExecution=\{day\.meal_execution\} mealKeys=\{meals\.map\(\(meal\) => meal\.key\)\} \/>\}/);
  assertSourceMatch(calendarizedDayDetail, /beforeNutrition=\{meal\.key \? <MealCompletionToggleCard/);
  assertSourceMatch(calendarizedDayDetail, /onToggleCompleted=\{\(mealKey, completed\) => void toggleMealCompletion\(mealKey, completed\)\}/);
  assertSourceMatch(calendarizedDayDetail, /action: completed \? "completed" : "skipped"/);
  assertSourceMatch(calendarizedDayDetail, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assertSourceMatch(calendarizedDayDetail, /<SectionDivider \/>[\s\S]*title="Detalle de cada Comida"/);
  assertSourceMatch(calendarizedDayDetail, /snapshotDailyPlanFoodPanelItems\(meals\)/);
  assertSourceMatch(calendarizedDayDetail, /<SectionDivider \/>[\s\S]*title="Alimentos en este plan diario"[\s\S]*<FoodPanels items=\{foods\} onOpenItem=/);

  assertSourceMatch(sharedEntityPanels, /PanelItemName\(\{ item, style = styles\.gridLeadingCell \}/);
  assertSourceMatch(sharedEntityPanels, /<PanelItemName item=\{item\} style=\{styles\.quantityLeadingCell\} \/>/);
  assertSourceMatch(sharedEntityPanels, /quantityLeadingCell: \{[^}]*flex: 1/);
  assertSourceMatch(sharedEntityPanels, /quantityValue: \{ textAlign: "center", width: 56 \}/);
  assertSourceMatch(sharedEntityPanels, /function PanelHeaderCell/);
  assertSourceMatch(sharedEntityPanels, /headerCell: \{[^}]*alignSelf: "stretch"[^}]*justifyContent: "center"/);
  assertSourceMatch(sharedEntityPanels, /<PanelHeaderCell \{\.\.\.sorting\} align="left" sortKey="name" style=\{styles\.gridLeadingCell\}>\{leadingLabel\}<\/PanelHeaderCell>/);
  assertSourceDoesNotMatch(sharedEntityPanels, /<Text style=\{\[styles\.headerText, styles\.gridLeadingCell/);
  assertSourceDoesNotMatch(sharedEntityPanels, /styles\.name, styles\.gridLeadingCell/);

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
  assertSourceMatch(programDailyPlan, /label=\{`Ir al detalle del plan de \$\{dayLabel\}`\}/);
  assertSourceMatch(programDailyPlan, /router\.push\(`\/libraries\/daily-plans\/\$\{day\.dailyplan_id\}` as Href\)/);
  assertSourceMatch(programDailyPlan, /\{day\?\.dailyplan_id \? \(/);
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

  assertSourceMatch(gallery, /Siempre abajo y sin bordes/);
  assertSourceMatch(gallery, /EntityCardAction/);

  const programChart = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"),
    "utf8",
  );
  assertSourceMatch(programChart, /import \{ Card, EntityHeading, layoutStyles \} from "@\/components\/ui"/);
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
  assertSourceMatch(programDetail, /axisLeadingLabel="Semana"/);
  assertSourceMatch(programChart, /weeks\.flatMap\(\(week\) => week\.days\.map/);
  assertSourceMatch(programChart, /axisLabels = \["S1", "S2"\]/);
  assertSourceMatch(programChart, /width < 600[\s\S]*?\? \{ width: "40%" as const \}/);
  assertSourceMatch(programChart, /strokeWidth="5"[^\n]*x1=\{x\} x2=\{x\} y1=\{y\} y2=\{y\}/);
  assertSourceMatch(programChart, /P \{allocationRange\(liveAllocationValues, 0/);
  assertSourceMatch(programChart, /const hasAllocation = protein \+ carbs \+ fat > 0/);
  assertSourceMatch(planningControls, /key=\{day\.id\}/);
  assertSourceMatch(programDetail, /axisLabels=\{liveWeeks\.map\(\(week\) => `S\$\{week\.week_number\}`\)\}/);
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
  assertSourceMatch(programDayPanels, /calorieShareDataCell: \{ flex: 1\.35 \}/);
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
