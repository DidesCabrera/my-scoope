import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { MobileApiError, userFacingError } from "../src/api/errors";
import { tokens } from "../src/generated/ui-tokens";

test("mobile visual grammar exposes the reusable card and nutrition tokens", () => {
  assert.equal(tokens.contract, "myscoope.visual-grammar.v2");
  assert.equal(tokens.radius.card, 22);
  assert.equal(tokens.color.surfaceApp, "#000000");
  for (const key of ["protein", "carbs", "fat", "kcalSurface", "allocationBarTrack", "allocationPanelTrack", "food", "meal", "dailyPlan", "dpm", "program"] as const) {
    assert.match(tokens.color[key], /^#[0-9A-F]{6}$/);
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
  const gallery = await readFile(
    path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"),
    "utf8",
  );
  assert.match(gallery, /export default function UiGalleryScreen/);
  assert.match(gallery, /if \(!__DEV__\) return <Redirect href="\/" \/>/);
  assert.match(gallery, /Galería del sistema UI/);
  assert.match(gallery, /Card-child de programa/);
  assert.match(gallery, /ProgramChildCard/);
  assert.match(gallery, /Detalle de programa/);
  assert.match(gallery, /ProgramDetailPreview/);
  assert.match(gallery, /ProgramActiveKpis/);
  assert.match(gallery, /KPI de programa en curso/);
  assert.match(gallery, /title="Colores de superficies"/);
  for (const surface of ["surfaceApp", "surfacePage", "surfaceCard", "surfaceMuted", "surfaceElevated"]) {
    assert.match(gallery, new RegExp(surface));
  }

  const nutritionKpi = await readFile(
    path.resolve(process.cwd(), "src/components/nutrition/nutrition-kpi-section.tsx"),
    "utf8",
  );
  assert.match(nutritionKpi, /borderColor: tokens\.color\.kcalBorder/);
  assert.match(nutritionKpi, /borderRadius: tokens\.component\.nutritionKpi\.regular\.totalRadius/);
  assert.match(nutritionKpi, /height: tokens\.component\.nutritionKpi\.regular\.totalSize/);
  assert.match(nutritionKpi, /height: tokens\.component\.nutritionKpi\.nested\.totalSize/);
  assert.match(nutritionKpi, /variant\?: "nested" \| "regular"/);
  assert.doesNotMatch(nutritionKpi, /density\?: "compact" \| "regular"/);
  assert.doesNotMatch(nutritionKpi, /height: compact \? "100%"/);

  const libraryCard = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"),
    "utf8",
  );
  assert.match(libraryCard, /NutritionEntityCard.*from "@\/components\/nutrition"/);
  assert.doesNotMatch(libraryCard, /\.\/nutrition-entity-card/);

  const collectionPageHeader = await readFile(
    path.resolve(process.cwd(), "src/components/ui/collection-page-header.tsx"),
    "utf8",
  );
  assert.match(collectionPageHeader, /container: \{ alignItems: "flex-start", gap: tokens\.spacing\.sm/);
  assert.match(collectionPageHeader, /iconSlot: \{ alignSelf: "flex-start" \}/);
  assert.match(collectionPageHeader, /function PageHeader[\s\S]*<View style=\{styles\.copy\}>[\s\S]*?<Text style=\{styles\.title\}>\{title\}<\/Text>[\s\S]*\{indicator\}/);
  assert.doesNotMatch(collectionPageHeader, /Bookmark|Mis librerías|eyebrow/);
  assert.match(collectionPageHeader, /<StructuralIndicators[^\n]*tone="surfaceMuted"/);
  assert.match(collectionPageHeader, /export function SectionPageHeader/);
  assert.match(collectionPageHeader, /<SectionIcon section=\{section\} size="hero" \/>/);
  assert.match(collectionPageHeader, /style=\{styles\.countChip\}/);

  for (const [relativePath, section, title] of [
    ["src/app/comparator/index.tsx", "comparator", "Comparador"],
    ["src/app/assistant/index.tsx", "chat", "Asistente AI"],
  ]) {
    const sectionScreen = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(sectionScreen, new RegExp(`<SectionPageHeader[^>]*section="${section}"[^>]*title="${title}"`));
    assert.doesNotMatch(sectionScreen, /<AppHeader/);
  }

  const productUiSourceForIndicators = await readFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assert.match(productUiSourceForIndicators, /chat: Sparkles/);
  assert.match(productUiSourceForIndicators, /proposal: ClipboardCheck/);
  assert.match(productUiSourceForIndicators, /comparator: Scale/);
  assert.match(productUiSourceForIndicators, /tone\?: "identity" \| "surfaceCard" \| "surfaceMuted"/);
  assert.match(productUiSourceForIndicators, /itemTone === "surfaceMuted" \? tokens\.color\.surfaceMuted : color/);
  assert.match(productUiSourceForIndicators, /structuralItemSurface: \{ borderColor: tokens\.color\.borderDefault, borderWidth: 1 \}/);

  const menuPanelSource = await readFile(
    path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"),
    "utf8",
  );
  assert.match(menuPanelSource, /menuFoods: \{ color: tokens\.color\.textMain/);
  assert.doesNotMatch(menuPanelSource, /menuFoods: \{[^}]*opacity:/);

  const libraryEntityPanels = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"),
    "utf8",
  );
  assert.match(libraryEntityPanels, /perKilogram: item\.protein_per_kilogram/);
  assert.match(libraryEntityPanels, /eyebrow=\{`Comida \$\{index \+ 1\}`\}/);
  assert.doesNotMatch(libraryEntityPanels, /mealCardMarker|mealCardNumber|mealCardLine/);

  for (const relativePath of [
    "src/app/program/days/[id].tsx",
    "src/components/details/dailyplan-meal-detail-list.tsx",
  ]) {
    const dailyPlanMealCards = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(dailyPlanMealCards, /eyebrow=\{`Comida \$\{index \+ 1\}`\}/);
    assert.doesNotMatch(dailyPlanMealCards, /mealCardMarker|mealCardNumber|mealCardLine|markerNumber|markerLine/);
  }
  assert.doesNotMatch(libraryEntityPanels, /protein: \{ grams: item\.protein_grams, allocation: item\.protein_allocation, perKilogram: null \}/);

  const programWeekPanels = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-week-comparison-panels.tsx"),
    "utf8",
  );
  assert.match(programWeekPanels, /EntityPanelTabs/);
  assert.match(programWeekPanels, /PanelSurface/);
  assert.match(programWeekPanels, /MacroCalorieDistribution/);
  assert.match(programWeekPanels, /PanelAllocationBar/);
  for (const tab of ["Calorías", "Macros", "Alloc", "Editar"]) assert.match(programWeekPanels, new RegExp(tab));
  assert.doesNotMatch(programWeekPanels, /label: "Semanas"/);
  assert.match(programWeekPanels, /<Pencil/);
  assert.match(programWeekPanels, /weekName: \{ color: tokens\.color\.textMain/);
  assert.match(programWeekPanels, /cell: \{[^}]*fontSize: tokens\.type\.caption/);
  assert.match(programWeekPanels, /row: \{[^}]*minHeight: 48/);
  assert.doesNotMatch(programWeekPanels, /cell: \{[^}]*fontSize: 11/);
  assert.doesNotMatch(programWeekPanels, /<PanelAllocationBar size="compact"/);
  assert.match(programWeekPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assert.doesNotMatch(programWeekPanels, /deltaUp|deltaDown|styles\.protein|styles\.carbs|styles\.fat/);

  const programDetail = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  assert.match(programDetail, /ProgramDailyPlanPreview/);
  assert.match(programDetail, /ProgramDayComparisonPanels/);
  assert.match(programDetail, /weekData\.foods \?\? \[\]\)\.map\(foodItem\)/);
  assert.match(programDetail, /: weekFoodItems/);
  assert.match(programDetail, /useState<number \| null>\(\(\) => filledDays\[0\] \? 0 : null\)/);
  assert.match(programDetail, /<View style=\{styles\.weekContent\}>/);
  assert.doesNotMatch(programDetail, /<Card(?: muted)? style=\{styles\.weekCard\}>/);
  assert.match(programDetail, /<ProgramDaySelector/);
  assert.match(programDetail, /<ProgramWeekTabs/);
  assert.match(programDetail, /detail=\{`\$\{weeksCount\} \$\{weeksCount === 1 \? "semana" : "semanas"\}`\}/);
  assert.match(programDetail, /title="Planificación semanal"/);
  assert.doesNotMatch(programDetail, /MajorSectionTitle/);
  assert.match(programDetail, /<ProgramWeekHeading week=\{week\} \/>/);
  assert.match(programDetail, /weekContent: \{[^}]*paddingTop: tokens\.spacing\.md/);
  assert.doesNotMatch(programDetail, /weekEyebrow|weekEyebrowText/);
  assert.doesNotMatch(programDetail, /Planificación por semanas/);
  assert.doesNotMatch(programDetail, /planningIdentity|planningTitle/);
  assert.match(programDetail, /weekContent: \{ gap: tokens\.spacing\.lg, minWidth: 0, paddingTop: tokens\.spacing\.md, width: "100%" \}/);
  assert.match(programDetail, /<ProgramMetricPreview[^\n]*style=\{layoutStyles\.cardContentBleed\}/);
  assert.match(programDetail, /<FoodPanels items=\{weekData/);
  assert.doesNotMatch(programDetail, /<View style=\{layoutStyles\.cardContentBleed\}><(?:FoodPanels|ProgramDayComparisonPanels|ProgramWeekComparisonPanels)/);
  assert.match(programDetail, /stickyHeaderIndices=\{\[3\]\}/);
  assert.match(programDetail, /weekTabsSticky: \{ backgroundColor: tokens\.color\.surfaceApp, marginHorizontal:/);
  assert.doesNotMatch(programDetail, /weekTabsStickyPinned/);
  assert.doesNotMatch(programDetail, /weekTabsOffset|weekTabsPinned/);
  assert.match(programDetail, /paddingVertical: tokens\.spacing\.sm/);

  const planningControls = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-planning-controls.tsx"),
    "utf8",
  );
  assert.match(planningControls, /<WeekDaySelectionRing \/>/);
  assert.match(planningControls, /accessibilityState=\{\{ expanded:/);
  assert.match(planningControls, /backgroundColor: tokens\.color\.surfaceCard/);
  assert.match(planningControls, /backgroundColor: tokens\.color\.dailyPlan/);
  assert.match(planningControls, /<ClipboardList color=\{tokens\.color\.entityIconForeground\} size=\{14\}/);
  assert.match(planningControls, /<Plus color=\{tokens\.color\.textMain\} size=\{24\} \/>/);
  assert.match(planningControls, /borderRadius: tokens\.spacing\.compact, height: 24/);
  assert.match(planningControls, /dayCircle: \{[^}]*borderWidth: 1[^}]*height: 44[^}]*width: 44/);
  assert.match(planningControls, /dayCircleCompact: \{ height: 40, width: 40 \}/);
  assert.match(planningControls, /hitSlop=\{compact \? 2 : undefined\}/);
  assert.match(planningControls, /<ScrollableTabBar[\s\S]*?tabs=\{weeks\.map/);
  assert.match(planningControls, /export function ProgramWeekHeading/);
  assert.match(planningControls, /<CalendarRange color=\{tokens\.color\.entityIconForeground\} size=\{11\}/);
  assert.match(planningControls, /weekHeadingTitle: \{[^}]*fontSize: tokens\.type\.section[^}]*fontWeight: tokens\.weight\.semibold/);

  const calendarizedPlanning = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"),
    "utf8",
  );
  assert.match(calendarizedPlanning, /<ProgramWeekHeading detail=\{weekDateRange\(weekDays\)\} week=\{activeWeek\} \/>/);
  assert.match(calendarizedPlanning, /style=\{styles\.weekContent\}/);
  assert.match(calendarizedPlanning, /weekContent: \{[^}]*paddingTop: tokens\.spacing\.md/);
  assert.doesNotMatch(calendarizedPlanning, /<Card style=\{styles\.weekCard\}>/);
  assert.match(calendarizedPlanning, /<ProgramWeekTabs/);
  assert.match(calendarizedPlanning, /<ProgramDaySelector/);
  assert.match(calendarizedPlanning, /apiRequest<CalendarizedDayDetail>/);
  assert.match(calendarizedPlanning, /<CalendarizedDailyPlanCard/);
  assert.match(calendarizedPlanning, /preferredCalendarizedDay\(days, week, localDate\(\)\)/);
  assert.match(calendarizedPlanning, /Día sin plan\. No hay un plan diario asignado para esta fecha\./);
  assert.match(calendarizedPlanning, /isToday: day\.calendar_date === localDate\(\)/);
  assert.match(calendarizedPlanning, /<SectionDivider spacing="compact" tone="soft" \/>/);
  assert.match(calendarizedPlanning, /title="Alimentos en esta semana"/);
  assert.match(calendarizedPlanning, /<FoodPanels items=\{weekFoods\} \/>/);

  const calendarizedDailyPlanCard = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-daily-plan-card.tsx"),
    "utf8",
  );
  assert.match(calendarizedDailyPlanCard, /<NutritionEntityCard/);
  assert.match(calendarizedDailyPlanCard, /<MealPanels/);
  assert.match(calendarizedDailyPlanCard, /onOpenItem=/);
  assert.match(calendarizedDailyPlanCard, /pathname: "\/program\/days\/\[id\]\/meals\/\[mealKey\]"/);
  assert.match(calendarizedDailyPlanCard, /mealKey: meal\.id/);
  assert.doesNotMatch(calendarizedDailyPlanCard, /kpiVariant="nested"/);
  assert.match(calendarizedDailyPlanCard, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assert.match(calendarizedDailyPlanCard, /completedCount: executions\.filter/);
  assert.match(calendarizedDailyPlanCard, /noteCount: executions\.filter/);
  assert.match(calendarizedDailyPlanCard, /label: "posición", value: `S\$\{position\.weekNumber\} · D\$\{position\.dayNumber\}`/);

  const calendarizedMealDetail = await readFile(
    path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"),
    "utf8",
  );
  assert.match(calendarizedMealDetail, /apiRequest<CalendarizedDayDetail>\(`\/api\/v1\/program\/days\/\$\{dayId\}`\)/);
  assert.match(calendarizedMealDetail, /day\.plan_snapshot\?\.meals\?\.find/);
  assert.match(calendarizedMealDetail, /<FoodPanels items=\{foods\} \/>[\s\S]*<MealAdherenceCheckIn/);
  assert.match(calendarizedMealDetail, /completion=\{\{/);
  assert.match(calendarizedMealDetail, /onChange=\{setExecution\}/);
  assert.doesNotMatch(calendarizedMealDetail, /\/api\/v1\/library\/meals/);

  const sharedEntityPanels = await readFile(
    path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"),
    "utf8",
  );
  assert.match(sharedEntityPanels, /accessibilityLabel=\{canOpen \? `Ver detalle de \$\{item\.name\}` : undefined\}/);
  assert.match(sharedEntityPanels, /<Pressable[\s\S]*style=\{\(\{ pressed \}\) => \[styles\.menuRow,[\s\S]*pressed && canOpen && styles\.menuRowPressed\]\}/);
  assert.doesNotMatch(sharedEntityPanels, /<Pressable[\s\S]*style=\{\(\{ pressed \}\) => \[styles\.menuAction/);
  assert.match(sharedEntityPanels, /<ChevronRight/);
  assert.match(sharedEntityPanels, /item\.time \? \([\s\S]*<Clock color=\{tokens\.color\.textMuted\} size=\{13\} strokeWidth=\{2\} \/>[\s\S]*<Text style=\{styles\.menuTime\}>\{item\.time\}<\/Text>/);
  assert.match(sharedEntityPanels, /item\.detailId != null \|\| item\.canOpen/);
  assert.match(sharedEntityPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);
  assert.match(libraryEntityPanels, /NutritionAllocationPanel/);

  const completionUi = await readFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assert.match(completionUi, /summarized=\{entity === "dailyPlan"\}/);
  assert.match(completionUi, /<CheckCheck color=\{tokens\.color\.textMuted\}/);
  assert.match(completionUi, /<Text style=\{styles\.completionIndicatorCount\}>\{completedCount\}<\/Text>/);
  assert.match(completionUi, /<Text style=\{styles\.completionIndicatorCount\}>\{noteCount\}<\/Text>/);
  assert.match(completionUi, /style=\{\[styles\.headingIndicators, page && styles\.headingIndicatorsPage\]\}/);
  assert.match(completionUi, /headingIndicatorsPage: \{ marginTop: tokens\.spacing\.xs \}/);

  const mealAdherence = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"),
    "utf8",
  );
  assert.match(mealAdherence, /accessibilityRole="checkbox"/);
  assert.match(mealAdherence, /onPress=\{\(\) => void saveStatus\(!completed\)\}/);
  assert.match(mealAdherence, /action: "note"/);
  assert.match(mealAdherence, /Guardar nota/);
  assert.match(mealAdherence, /Editar nota/);
  assert.match(mealAdherence, /<Pencil/);
  assert.match(mealAdherence, /onChange\?\.\(execution\)/);
  assert.match(mealAdherence, /maxLength=\{500\}/);
  assert.match(mealAdherence, /action: nextCompleted \? "completed" : "skipped"/);
  assert.match(mealAdherence, /<View style=\{styles\.divider\} \/>/);
  assert.match(mealAdherence, /<SectionHeading title="Cumplimiento de esta comida" \/>[\s\S]*<ContentPanel muted>/);
  assert.match(mealAdherence, /editingNote \? \([\s\S]*<TextInput[\s\S]*\) : \([\s\S]*styles\.noteText/);
  assert.doesNotMatch(mealAdherence, /statusLabel|styles\.status/);
  assert.doesNotMatch(mealAdherence, /Cumplimiento actualizado|Nota guardada|statusSaved|noteSaved/);
  assert.doesNotMatch(mealAdherence, /label=\{editingNote \? "Guardar nota" : "Editar nota"\}/);

  const activeProgram = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  assert.match(activeProgram, /<SectionPageHeader countLabel="semanas" section="calendarization" title="Mi programa activo" \/>/);
  assert.doesNotMatch(activeProgram, /<SectionPageHeader count=\{weekCount\}/);
  assert.doesNotMatch(activeProgram, /<CollectionPageHeader/);

  const appNavigation = await readFile(path.resolve(process.cwd(), "src/components/navigation/app-navigation.tsx"), "utf8");
  assert.match(appNavigation, /program: CalendarClock/);
  assert.match(appNavigation, /pathname\.startsWith\("\/program"\).*icon: CalendarClock/);
  assert.match(activeProgram, /stickyHeaderIndices=\{\[1\]\}/);
  assert.doesNotMatch(activeProgram, /weekTabsStickyPinned/);
  assert.match(activeProgram, /program\?\.weeks_count/);
  assert.match(activeProgram, /Array\.from\(\{ length: weekCount \}/);
  assert.match(activeProgram, /<ProgramWeekTabs activeWeek=\{activeWeek\}/);
  assert.match(activeProgram, /<CalendarizedProgramPlanning days=\{programDays\} initialWeek=\{activeWeek\} key=\{`\$\{calendarization\.id\}:\$\{activeWeek\}`\} showWeekTabs=\{false\} weeksData=\{program\.weeks\} \/>/);
  assert.match(activeProgram, /<SectionDivider \/>[\s\S]*<SectionHeading[^>]*title="Planificación Semanal"/);
  assert.match(activeProgram, /<CalendarizedProgramPlanning[\s\S]*<SectionDivider \/>[\s\S]*<DetailLinkRow/);
  assert.match(activeProgram, /label="Ver plantilla original"/);
  assert.match(activeProgram, /conserva lo que realmente ocurrió/);
  assert.match(activeProgram, /weekCount === 1 \? "semana" : "semanas"/);

  const activePlanningControls = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-planning-controls.tsx"), "utf8");
  assert.match(activePlanningControls, /<ScrollableTabBar/);
  assert.match(activePlanningControls, /tabs=\{weeks\.map/);

  const calendarizedPlanningActive = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"),
    "utf8",
  );
  assert.match(calendarizedPlanningActive, /compactMonthLabel\(day\.calendar_date\)/);
  assert.match(calendarizedPlanningActive, /left\.calendar_date\.localeCompare\(right\.calendar_date\)/);
  assert.match(calendarizedPlanningActive, /pickerHref\("dailyplan-to-calendarized-day", \{ dayId:/);
  assert.match(calendarizedPlanningActive, /label="Cambiar plan diario"/);

  const activeProgramOverview = await readFile(
    path.resolve(process.cwd(), "src/components/programs/program-active-card.tsx"),
    "utf8",
  );
  assert.match(activeProgramOverview, /<ProgramActiveKpis[^>]*bleed=\{false\}/);
  assert.match(activeProgramOverview, /eyebrow="Programa activo"/);
  assert.doesNotMatch(activeProgramOverview, /eyebrow="Programa en curso"/);
  assert.match(activeProgramOverview, /SectionHeading icon=\{<Activity[^>]*>\} title="Métricas de activación"/);
  assert.match(activeProgramOverview, /embedded \? <DetailLinkRow[\s\S]*router\.push\("\/program" as Href\)/);
  assert.match(activeProgramOverview, /indicators=\{\[\.\.\.\(embedded \? \[\] : program\.indicators\), \{ icon: "week", iconPosition: "leading", label: "periodo", tone: "surfaceMuted"/);
  assert.match(activeProgramOverview, /value: `\$\{compactDateLabel\(calendarization\.start_date\)\} — \$\{compactDateLabel\(calendarization\.end_date\)\}`/);
  assert.match(activeProgramOverview, /export function ProgramActiveHomeOverview[\s\S]*<ProgramActiveOverview \{\.\.\.props\} embedded/);
  assert.match(activeProgramOverview, /embedded[\s\S]*<Card accent=\{tokens\.color\.program\} style=\{styles\.content\}>\{content\}<\/Card>/);

  const activeProgramKpis = await readFile(
    path.resolve(process.cwd(), "src/components/programs/program-active-kpis.tsx"),
    "utf8",
  );
  assert.doesNotMatch(activeProgramKpis, /periodRow|periodDates|CalendarDays/);
  assert.doesNotMatch(activeProgramKpis, /kcalSurface|kcalBorder|periodBorder|periodText/);
  assert.match(activeProgramKpis, /indicatorsSurfaceReset:\{[^}]*padding:tokens\.spacing\.xs/);
  assert.match(activeProgramKpis, /Días recorridos/);
  assert.match(activeProgramKpis, /indicator:\{[^}]*padding:tokens\.spacing\.md/);
  assert.match(activeProgramKpis, /indicatorValue:\{[^}]*marginTop:tokens\.spacing\.sm/);
  assert.match(activeProgramKpis, /fraction:\{[^}]*fontSize:tokens\.type\.section/);
  assert.match(activeProgramKpis, /percentageText:\{[^}]*fontSize:tokens\.type\.section/);
  assert.match(activeProgramKpis, /percentageText:\{[^}]*color:tokens\.color\.textMain/);
  assert.match(activeProgramKpis, /<Text style=\{styles\.percentageText\}>\{advancement\}%<\/Text>/);
  assert.match(activeProgramKpis, /<Text style=\{styles\.percentageText\}>\{compliance\}%<\/Text>/);
  assert.doesNotMatch(activeProgramKpis, /percentageTag/);

  const activateProgram = await readFile(
    path.resolve(process.cwd(), "src/app/program/activate.tsx"),
    "utf8",
  );
  assert.match(activateProgram, /stickyHeaderIndices=\{\[0\]\}/);
  assert.match(activateProgram, /<PickerEntryTabs[\s\S]*createLabel="Crear Nuevo"/);
  assert.match(activateProgram, /accessibilityLabel="Buscar programa"/);
  assert.match(activateProgram, /pathname: "\/libraries\/create", params: \{ entity: "program" \}/);
  assert.match(activateProgram, /<ProgramChildCard[\s\S]*openActionLabel="Seleccionar"/);
  assert.match(activateProgram, /<ProgramChildCard[\s\S]*openActionLabel="Cambiar selección"/);
  assert.match(activateProgram, /<SectionHeading title="Configura la selección" \/>/);
  assert.match(activateProgram, /label="Calendarizar programa"/);
  assert.doesNotMatch(activateProgram, /PASO 3 DE 3|Confirma la calendarización|Volver a configurar/);

  const todayScreen = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  assert.match(todayScreen, /<AppHeader[\s\S]*?title=\{`Vamos, \$\{firstName\}`\}[\s\S]*?\/>[\s\S]*<CurrentWeekSection localDate=\{today\.local_date\} \/>/);
  assert.doesNotMatch(todayScreen, /<AppHeader eyebrow=/);
  assert.ok(todayScreen.indexOf("<CurrentWeekSection") < todayScreen.indexOf("<CalendarizedDailyPlanCard"));
  assert.match(todayScreen, /<CurrentWeekSection[\s\S]*?<HomeSectionTitle>\{`Tu Plan para hoy, \$\{homePlanDateLabel\(today\.local_date\)\}`\}<\/HomeSectionTitle>[\s\S]*?<CalendarizedDailyPlanCard/);
  assert.ok(todayScreen.indexOf("<CalendarizedDailyPlanCard") < todayScreen.indexOf("<ProgramActiveHomeOverview"));
  assert.match(todayScreen, /<CalendarizedDailyPlanCard[\s\S]*?<HomeSectionTitle>Tu Programa Activo<\/HomeSectionTitle>[\s\S]*?<ProgramActiveHomeOverview/);
  assert.match(todayScreen, /homeSectionTitle: \{[^}]*fontSize: 18[^}]*marginBottom: -tokens\.spacing\.sm[^}]*marginTop: tokens\.spacing\.sm/);
  assert.doesNotMatch(todayScreen, /<SectionDivider \/>/);
  const currentWeek = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/current-week-section.tsx"),
    "utf8",
  );
  assert.doesNotMatch(currentWeek, /Semana en curso|<SectionHeading/);
  assert.match(currentWeek, /<Text[^>]*styles\.monthLabel[^>]*>\{day\.monthLabel\}<\/Text>/);
  assert.match(currentWeek, /dayCircle: \{[^}]*backgroundColor: tokens\.color\.surfaceCard[^}]*height: 44[^}]*width: 44/);
  assert.match(currentWeek, /monthLabel: \{[^}]*fontFamily: font\.regular[^}]*fontSize: 9[^}]*fontWeight: "300"[^}]*lineHeight: 10/);
  assert.match(currentWeek, /monthLabelToday: \{ color: tokens\.color\.surfaceApp, fontWeight: tokens\.weight\.regular \}/);
  assert.match(currentWeek, /<WeekDaySelectionRing \/>/);
  assert.match(currentWeek, /dayCircleToday: \{ backgroundColor: tokens\.color\.entityIconForeground \}/);
  assert.match(currentWeek, /dayNumberToday: \{ color: tokens\.color\.surfaceApp \}/);
  assert.match(currentWeek, /compact && styles\.dayCircleCompact/);
  assert.match(currentWeek, /dayCircleCompact: \{ height: 40, width: 40 \}/);
  const weekDayGrid = await readFile(
    path.resolve(process.cwd(), "src/components/ui/week-day-grid.tsx"),
    "utf8",
  );
  assert.match(weekDayGrid, /const compactWeekDayWidth = 350/);
  assert.match(weekDayGrid, /gridCompact: \{ gap: tokens\.spacing\.xs \}/);
  assert.match(weekDayGrid, /cell: \{[^}]*flex: 1[^}]*gap: tokens\.spacing\.sm/);
  assert.match(weekDayGrid, /stopColor="#D62976"/);
  assert.match(weekDayGrid, /strokeWidth="6"/);
  assert.match(weekDayGrid, /selectionRing: \{ bottom: -7, left: -7[^}]*right: -7, top: -7 \}/);
  assert.match(gallery, /key: "calendars", label: "Calendarios"/);
  assert.match(gallery, /\{ label: "iPhone XR", width: 414 \}/);
  assert.match(gallery, /\{ label: "Teléfono compacto", width: 375 \}/);
  assert.match(gallery, /<CurrentWeekSection localDate="2026-09-01" \/>/);
  assert.match(gallery, /title="Vamos, Felipe"/);
  assert.match(gallery, /<GuideMetric label="Peso actual" value="85,0kg" \/>/);
  assert.match(gallery, /<ProgramDaySelector/);
  assert.match(gallery, /MI PROGRAMA ACTIVO · FECHAS \+ PLANES/);
  assert.match(todayScreen, /<ProgramActiveHomeOverview/);
  assert.match(todayScreen, /alignment="center"/);
  assert.match(todayScreen, /<GuideMetric icon="weight" value=\{`\$\{displayWeight\(currentWeightKg\)\} kg`\} \/>/);
  assert.doesNotMatch(todayScreen, /GuideMetric label="Peso actual"/);
  assert.match(productUiSourceForIndicators, /guideMetricValueOnly: \{ borderRadius: tokens\.radius\.lg, minHeight: 40 \}/);
  assert.match(todayScreen, /apiRequest<WeightListData>\("\/api\/v1\/weights\?limit=1"\)/);
  assert.match(todayScreen, /latestWeightKg \?\? profile\?\.current_weight_kg \?\? today\?\.measurements\?\.latest_weight_kg/);
  assert.match(todayScreen, /displayWeight\(currentWeightKg\)/);
  assert.match(todayScreen, /dateLabel=\{compactDateLabel\(today\.local_date\)\}/);
  assert.match(todayScreen, /<HomeLibraryGrid counts=\{libraryCounts\} \/>/);
  assert.match(todayScreen, /\/api\/v1\/library\/programs\?limit=1/);
  const homeLibraryGrid = await readFile(
    path.resolve(process.cwd(), "src/components/home/home-library-grid.tsx"),
    "utf8",
  );
  assert.match(homeLibraryGrid, /<Bookmark[^>]*>[\s\S]*Mis librerías/);
  assert.match(homeLibraryGrid, /flexWrap: "wrap"/);
  assert.match(homeLibraryGrid, /Mis Programas\\nSemanales/);
  assert.match(homeLibraryGrid, /Mis Planes\\nDiarios/);
  assert.match(homeLibraryGrid, /Mis Comidas/);
  assert.match(homeLibraryGrid, /Mis Alimentos/);
  assert.match(homeLibraryGrid, /pathname: "\/libraries\/create", params: \{ entity: entry\.entity \}/);
  assert.match(homeLibraryGrid, /section: \{[^}]*marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);
  assert.match(homeLibraryGrid, /padding: tokens\.card\.outerPadding/);
  assert.match(homeLibraryGrid, /<SectionDivider spacing="compact" \/>/);
  assert.match(homeLibraryGrid, /borderTopColor: tokens\.color\[entry\.entity\]/);
  assert.match(homeLibraryGrid, /borderTopWidth: 3/);
  assert.match(homeLibraryGrid, /title: \{[^}]*fontSize: tokens\.type\.body/);
  assert.doesNotMatch(homeLibraryGrid, /description:/);
  assert.doesNotMatch(todayScreen, /<ProgramActiveCard/);
  assert.match(todayScreen, /activeProgram\?\.days\.find\(\(day\) => day\.id === today\?\.day_id\)/);
  assert.match(todayScreen, /position=\{todayProgramDay \? \{ dayNumber: todayProgramDay\.day_number, weekNumber: todayProgramDay\.week_number \} : undefined\}/);
  assert.doesNotMatch(activeProgram, /program\?\.days\.map/);

  const libraryDetail = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"),
    "utf8",
  );
  assert.match(libraryDetail, /<ProgramDetailPreview[\s\S]*?scrollable\s*\/>/);
  assert.match(libraryDetail, /FoodPanels, MealPanels.*from "@\/components\/panels"/);
  assert.match(libraryDetail, /title="Alimentos en este plan diario"><FoodPanels items=\{item\.panel\.foods\.map\(foodPanelItem\)\}/);
  assert.match(libraryDetail, /<SectionDivider \/><EntityDetailSection[^>]*title="Detalle de cada Comida"/);
  assert.match(libraryDetail, /<SectionDivider \/><EntityDetailSection[^>]*title="Alimentos en este plan diario"/);

  const calendarizedDayDetail = await readFile(
    path.resolve(process.cwd(), "src/app/program/days/[id].tsx"),
    "utf8",
  );
  assert.match(calendarizedDayDetail, /<FoodPanels items=\{foods\} \/>/);
  assert.match(calendarizedDayDetail, /perKilogram: totals\?\.protein_per_kilogram \?\? null/);
  assert.match(calendarizedDayDetail, /<SectionDivider \/>[\s\S]*title="Detalle de cada Comida"/);
  assert.match(calendarizedDayDetail, /snapshotDailyPlanFoodPanelItems\(meals\)/);
  assert.match(calendarizedDayDetail, /<SectionDivider \/>[\s\S]*title="Alimentos en este plan diario"[\s\S]*<FoodPanels items=\{foods\} \/>/);

  assert.match(sharedEntityPanels, /PanelItemName\(\{ item, style = styles\.gridLeadingCell \}/);
  assert.match(sharedEntityPanels, /<PanelItemName item=\{item\} style=\{styles\.quantityLeadingCell\} \/>/);
  assert.match(sharedEntityPanels, /quantityLeadingCell: \{[^}]*flex: 1/);
  assert.match(sharedEntityPanels, /quantityValue: \{ textAlign: "center", width: 56 \}/);
  assert.match(sharedEntityPanels, /function PanelHeaderCell/);
  assert.match(sharedEntityPanels, /headerCell: \{[^}]*alignSelf: "stretch"[^}]*justifyContent: "center"/);
  assert.match(sharedEntityPanels, /<PanelHeaderCell align="left" style=\{styles\.gridLeadingCell\}>\{leadingLabel\}<\/PanelHeaderCell>/);
  assert.doesNotMatch(sharedEntityPanels, /<Text style=\{\[styles\.headerText, styles\.gridLeadingCell/);
  assert.doesNotMatch(sharedEntityPanels, /styles\.name, styles\.gridLeadingCell/);

  assert.match(libraryEntityPanels, /FoodPanels as SharedFoodPanels/);
  assert.match(libraryEntityPanels, /MealPanels as SharedMealPanels/);
  assert.match(libraryEntityPanels, /return <SharedFoodPanels items=\{items\.map\(toFoodPanelItem\)\} \/>/);
  assert.match(libraryEntityPanels, /return <SharedMealPanels items=\{items\.map\(toMealPanelItem\)\} \/>/);

  const calendarizationAdapters = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/presentation-adapters.ts"),
    "utf8",
  );
  assert.match(calendarizationAdapters, /export function snapshotDailyPlanFoodPanelItems/);
  assert.match(calendarizationAdapters, /current\.quantity \+= food\.quantity_g \?\? 0/);

  const sectionDivider = await readFile(
    path.resolve(process.cwd(), "src/components/ui/section-divider.tsx"),
    "utf8",
  );
  assert.match(sectionDivider, /export function SectionDivider/);
  assert.match(sectionDivider, /marginBottom: tokens\.spacing\.sm, marginTop: tokens\.spacing\.lg/);
  assert.match(gallery, /title="Separador de secciones"/);

  const entityDetail = await readFile(
    path.resolve(process.cwd(), "src/components/details/entity-detail-page.tsx"),
    "utf8",
  );
  const pageCardStyle = entityDetail.match(/pageCard: \{([^}]+)\}/)?.[1] ?? "";
  assert.doesNotMatch(pageCardStyle, /backgroundColor/);
  assert.doesNotMatch(pageCardStyle, /border(?:Color|Radius|TopWidth|Width)/);
  assert.doesNotMatch(pageCardStyle, /padding(?:Top|:)/);
  assert.doesNotMatch(entityDetail, /borderTopColor: tokens\.color\[entity\]/);

  const programDailyPlan = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-daily-plan-preview.tsx"),
    "utf8",
  );
  assert.match(programDailyPlan, /day \? \(day\.meals \?\? \[\]\)\.map\(mealPanelItem\) : meals/);
  assert.match(programDailyPlan, /label=\{`Ir al detalle del plan de \$\{dayLabel\}`\}/);
  assert.match(programDailyPlan, /router\.push\(`\/libraries\/daily-plans\/\$\{day\.dailyplan_id\}` as Href\)/);
  assert.match(programDailyPlan, /\{day\?\.dailyplan_id \? \(/);
  assert.match(programDailyPlan, /actions=\{\(/);
  assert.doesNotMatch(programDailyPlan, /accessory=\{\(/);
  assert.doesNotMatch(programDailyPlan, /kpiVariant="nested"|subtitle="Plan diario asignado"|label: "plan asignado"/);
  assert.match(programDailyPlan, /label: "posición"/);
  assert.match(programDailyPlan, /icon: "meal", label: "comidas"/);
  assert.match(programDailyPlan, /onOpenItem=\{\(meal\) =>/);

  const productUiSource = await readFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assert.match(productUiSource, /export function EntityCardActions/);
  assert.match(productUiSource, /export function EntityCardAction/);
  assert.match(productUiSource, /entityCardAction: \{ alignItems: "center", borderRadius:/);
  assert.doesNotMatch(productUiSource, /entityCardAction: \{[^\n]*borderWidth/);
  assert.match(productUiSource, /entityCardPanelSlot: \{ minWidth: 0 \}/);

  const panelSurface = await readFile(
    path.resolve(process.cwd(), "src/components/panels/panel-surface.tsx"),
    "utf8",
  );
  assert.match(panelSurface, /marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding/);

  assert.match(gallery, /Siempre abajo y sin bordes/);
  assert.match(gallery, /EntityCardAction/);

  const programChart = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"),
    "utf8",
  );
  assert.match(programChart, /import \{ Card, EntityHeading, layoutStyles \} from "@\/components\/ui"/);
  assert.doesNotMatch(programChart, /Card.*from "@\/components\/ui\/primitives"/);
  assert.match(programChart, /<Card accent=\{tokens\.color\.program\}>/);
  assert.match(programChart, /<ProgramMetricPreview[^\n]*style=\{layoutStyles\.cardContentBleed\}/);
  assert.doesNotMatch(programChart, /footer: \{[^}]*borderTop/);
  assert.match(programChart, /allocationSlot: \{[^\n]*gap: 2[^\n]*paddingHorizontal: 1/);
  assert.match(programChart, /allocationSegment: \{ borderRadius: 2/);
  assert.match(programChart, /key=\{`\$\{index\}-\$\{label\}`\} style=\{styles\.weekLabelCell\}/);
  assert.match(programChart, /export function programDailyMetricData/);
  assert.match(programChart, /lastWeek === 1 \? "Semana 1" : `Semanas 1-\$\{lastWeek\}`/);
  assert.match(programChart, /style=\{\[styles\.axisChip, styles\.axisLeadingChip\]\}/);
  assert.match(programChart, /axisLeadingChip: \{[^}]*textAlign: "left"[^}]*width: "100%"/);
  assert.match(programChart, /plotViewportWidth \* Math\.max\(1, axisLabels\.length \/ 8\)/);
  assert.match(programChart, /<ScrollView[\s\S]*horizontal[\s\S]*showsHorizontalScrollIndicator=\{axisLabels\.length > 8\}/);
  assert.match(programChart, /index > 0 && index % 7 === 0 && styles\.weekDivider/);
  assert.doesNotMatch(programChart, /weekLabels: \{[^}]*paddingHorizontal/);
  assert.doesNotMatch(programChart, /weekLabels: \{[^}]*gap:/);
  assert.match(programChart, /weekLabelCell: \{ flex: 1, minWidth: 0, paddingHorizontal: 1 \}/);
  assert.match(programChart, /\(index \+ 0\.5\) \* \(140 \/ slotCount\)/);
  assert.match(programChart, /\(index \+ 1\) \* 7 \* \(140 \/ slotCount\)/);
  assert.doesNotMatch(programChart, /metricPlot: \{[^}]*paddingHorizontal/);
  assert.match(programDetail, /axisLeadingLabel="Semana"/);
  assert.match(programChart, /weeks\.flatMap\(\(week\) => week\.days\.map/);
  assert.match(programChart, /axisLabels = \["S1", "S2"\]/);
  assert.match(programChart, /width < 600[\s\S]*?\? \{ width: "40%" as const \}/);
  assert.match(programChart, /strokeWidth="5"[^\n]*x1=\{x\} x2=\{x\} y1=\{y\} y2=\{y\}/);
  assert.match(programChart, /P \{allocationRange\(liveAllocationValues, 0/);
  assert.match(programChart, /const hasAllocation = protein \+ carbs \+ fat > 0/);
  assert.match(planningControls, /key=\{day\.id\}/);
  assert.match(programDetail, /axisLabels=\{liveWeeks\.map\(\(week\) => `S\$\{week\.week_number\}`\)\}/);
  assert.match(programDetail, /const liveMetricData = weekData \? programDailyMetricData\(\[weekData\]\) : undefined/);
  assert.doesNotMatch(programDetail, /weekData\.days\.filter\(\(day\) => day\.nutrition\)/);

  const libraryCardSource = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"),
    "utf8",
  );
  assert.match(libraryCardSource, /programDailyMetricData\(item\.panel\.weeks\)/);
  assert.match(libraryCardSource, /`S\$\{week\.week_number\}`/);

  const layoutUiSource = await readFile(
    path.resolve(process.cwd(), "src/components/ui/layout.tsx"),
    "utf8",
  );
  assert.match(layoutUiSource, /cardContentBleed: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);

  const programDayPanels = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-day-comparison-panels.tsx"),
    "utf8",
  );
  assert.match(programDayPanels, /EntityPanelTabs/);
  assert.match(programDayPanels, /MacroCalorieDistribution/);
  assert.match(programDayPanels, /PanelAllocationBar/);
  assert.match(programDayPanels, /<Pencil/);
  assert.match(programDayPanels, /cell: \{[^}]*fontSize: tokens\.type\.caption/);
  assert.match(programDayPanels, /planName: \{[^}]*fontSize: tokens\.type\.label/);
  assert.doesNotMatch(programDayPanels, /cell: \{[^}]*fontSize: 11/);
  assert.doesNotMatch(programDayPanels, /<PanelAllocationBar size="compact"/);
  assert.match(programDayPanels, /<ProteinPerKilogramBadge showUnit=\{false\} style=\{styles\.ppkBadge\}/);
  assert.match(programDayPanels, /ppkBadge: \{ height: 24, minHeight: 24 \}/);
  assert.match(programDayPanels, /calorieShareDataCell: \{ flex: 1\.35 \}/);
  assert.match(programDayPanels, /ppkDataCell: \{ flex: 0\.65 \}/);
  assert.match(programDayPanels, /column === "% Cal" && styles\.calorieShareDataCell/);
  assert.match(programDayPanels, /column === "PPK" && styles\.ppkDataCell/);
  assert.match(programDayPanels, /allocationRow: \{ gap: tokens\.spacing\.sm \}/);

  const programMetricPanels = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"),
    "utf8",
  );
  assert.match(programMetricPanels, /metricTitle: \{[^}]*fontSize: tokens\.type\.body/);
  assert.match(programMetricPanels, /metricIdentity: \{[^}]*height: 58/);
  assert.match(programMetricPanels, /allocationIdentity: \{ height: 94/);
  assert.match(programMetricPanels, /rangeBadge: \{[^}]*fontSize: tokens\.type\.label/);
  assert.match(programMetricPanels, /axisChip: \{[^}]*fontSize: tokens\.type\.label/);
  assert.match(programMetricPanels, /axisChip: \{[^}]*backgroundColor: "transparent"[^}]*borderColor: tokens\.color\.borderDefault[^}]*borderWidth: 1[^}]*color: tokens\.color\.textMuted/);
  assert.match(programMetricPanels, /allocationRange: \{[^}]*fontSize: tokens\.type\.label/);
  assert.match(programMetricPanels, /width < 600[\s\S]*\? \{ width: "40%" as const \}/);

  const productUi = await readFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assert.match(productUi, /const structuralIndicatorColors/);
  assert.match(productUi, /food: tokens\.color\.food/);
  assert.match(productUi, /meal: tokens\.color\.meal/);
  assert.match(productUi, /dailyPlan: tokens\.color\.dailyPlan/);
  assert.doesNotMatch(productUi, /styles\.structuralDivider/);
});

test("the committed mobile contract exposes every route consumed through CML08", async () => {
  const file = path.resolve(process.cwd(), "../docs/00_current/api/mobile-v1.openapi.json");
  const schema = JSON.parse(await readFile(file, "utf8")) as { info: { version: string }; paths: Record<string, unknown> };
  assert.equal(schema.info.version, "1.0.0");
  for (const route of [
    "/api/v1/session",
    "/api/v1/sessions/{device_session_id}",
    "/api/v1/me",
    "/api/v1/onboarding",
    "/api/v1/today",
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
  const schema = JSON.parse(await readFile(file, "utf8")) as {
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
  const metadata = JSON.parse(await readFile(path.join(store, "metadata/es-CL.json"), "utf8"));
  const privacy = JSON.parse(await readFile(path.join(store, "privacy-labels.json"), "utf8"));
  const screenshots = JSON.parse(await readFile(path.join(store, "screenshots/manifest.json"), "utf8"));
  const notes = await readFile(path.join(store, "review-notes.es-CL.md"), "utf8");

  assert.ok(metadata.name.length <= 30);
  assert.ok(metadata.subtitle.length <= 30);
  assert.ok(Buffer.byteLength(metadata.keywords, "utf8") <= 100);
  assert.match(metadata.privacy_policy_url, /^https:\/\//);
  assert.match(metadata.support_url, /^https:\/\//);
  assert.equal(privacy.tracking, false);
  assert.equal(screenshots.shots.length, 5);
  assert.ok(screenshots.shots.every((shot: { route: string }) => shot.route !== "/check-in"));
  assert.match(notes, /App Store Connect/);
  assert.doesNotMatch(notes, /check-in del día/i);
  assert.doesNotMatch(notes, /password\s*[=:]\s*\S+/i);
});

test("the iOS release contract declares only approved capabilities and privacy categories", async () => {
  const appFile = path.resolve(process.cwd(), "app.json");
  const app = JSON.parse(await readFile(appFile, "utf8")).expo as {
    ios: { usesAppleSignIn: boolean; privacyManifests: { NSPrivacyTracking: boolean; NSPrivacyCollectedDataTypes: { NSPrivacyCollectedDataType: string }[] } };
    plugins: (string | [string, Record<string, unknown>])[];
  };
  assert.equal(app.ios.usesAppleSignIn, true);
  assert.equal(app.ios.privacyManifests.NSPrivacyTracking, false);
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
    assert.match(message, new RegExp(fragment, "i"));
    assert.doesNotMatch(message, /raw provider detail/);
  }
  assert.match(userFacingError(new MobileApiError("failed", "assistant_turn_failed", 422)), /conversación anterior sigue guardada/i);
});
