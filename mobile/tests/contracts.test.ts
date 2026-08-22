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
  assert.match(collectionPageHeader, /container: \{ alignItems: "flex-start", flexDirection: "row"/);
  assert.match(collectionPageHeader, /iconSlot: \{ paddingTop: tokens\.spacing\.xs \}/);
  assert.match(collectionPageHeader, /copy: \{ alignItems: "flex-start", flex: 1/);
  assert.match(collectionPageHeader, /<View style=\{styles\.copy\}>[\s\S]*?<Text style=\{styles\.title\}>\{title\}<\/Text>[\s\S]*?<StructuralIndicators/);
  assert.match(collectionPageHeader, /<StructuralIndicators[^\n]*tone="surfaceMuted"/);

  const productUiSourceForIndicators = await readFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  assert.match(productUiSourceForIndicators, /tone\?: "identity" \| "surfaceCard" \| "surfaceMuted"/);
  assert.match(productUiSourceForIndicators, /tone === "surfaceMuted" \? tokens\.color\.surfaceMuted : color/);
  assert.match(productUiSourceForIndicators, /structuralItemSurface: \{ borderColor: tokens\.color\.borderDefault, borderWidth: 1 \}/);

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
  assert.match(programDetail, /<Card style=\{styles\.weekCard\}>/);
  assert.doesNotMatch(programDetail, /<Card muted style=\{styles\.weekCard\}>/);
  assert.match(programDetail, /<ProgramDaySelector/);
  assert.match(programDetail, /<ProgramWeekTabs/);
  assert.match(programDetail, /weekCard: \{ gap: tokens\.spacing\.lg, marginHorizontal: -tokens\.spacing\.screen \}/);
  assert.match(programDetail, /<ProgramMetricPreview[^\n]*style=\{layoutStyles\.cardContentBleed\}/);
  assert.match(programDetail, /<FoodPanels items=\{weekData/);
  assert.doesNotMatch(programDetail, /<View style=\{layoutStyles\.cardContentBleed\}><(?:FoodPanels|ProgramDayComparisonPanels|ProgramWeekComparisonPanels)/);
  assert.match(programDetail, /stickyHeaderIndices=\{\[3\]\}/);
  assert.match(programDetail, /weekTabsSticky: \{ backgroundColor: tokens\.color\.surfaceApp, borderBottomColor: "transparent", borderBottomWidth: 1/);
  assert.match(programDetail, /weekTabsStickyPinned: \{ borderBottomColor: tokens\.color\.borderDefault \}/);
  assert.match(programDetail, /contentOffset\.y >= weekTabsOffset\.current/);
  assert.match(programDetail, /paddingVertical: tokens\.spacing\.sm/);

  const planningControls = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/program-planning-controls.tsx"),
    "utf8",
  );
  assert.match(planningControls, /function SelectedDayRing/);
  assert.match(planningControls, /stopColor="#D62976"/);
  assert.match(planningControls, /accessibilityState=\{\{ expanded:/);
  assert.match(planningControls, /backgroundColor: tokens\.color\.surfaceCard/);
  assert.match(planningControls, /backgroundColor: tokens\.color\.dailyPlan/);
  assert.match(planningControls, /<ClipboardList color=\{tokens\.color\.entityIconForeground\} size=\{14\}/);
  assert.match(planningControls, /borderRadius: tokens\.spacing\.compact, height: 24/);
  assert.match(planningControls, /horizontal\n\s+showsHorizontalScrollIndicator=\{false\}/);

  const calendarizedPlanning = await readFile(
    path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"),
    "utf8",
  );
  assert.match(calendarizedPlanning, /title="Planes diarios esta semana"/);
  assert.match(calendarizedPlanning, /<ProgramWeekTabs/);
  assert.match(calendarizedPlanning, /<ProgramDaySelector/);
  assert.match(calendarizedPlanning, /apiRequest<CalendarizedDayDetail>/);
  assert.match(calendarizedPlanning, /<NutritionEntityCard/);

  const activeProgram = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  assert.match(activeProgram, /<CalendarizedProgramPlanning days=\{program\?\.days \?\? \[\]\} key=\{calendarization\.id\} \/>/);
  assert.doesNotMatch(activeProgram, /program\?\.days\.map/);

  const libraryDetail = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"),
    "utf8",
  );
  assert.match(libraryDetail, /<ProgramDetailPreview[\s\S]*?scrollable\s*\/>/);
  assert.match(libraryDetail, /FoodPanels, MealPanels.*from "@\/components\/panels"/);
  assert.match(libraryDetail, /title="Alimentos en este plan diario"><FoodPanels items=\{item\.panel\.foods\.map\(foodPanelItem\)\}/);

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
  assert.match(programChart, /allocationSlot: \{[^\n]*gap: 2[^\n]*paddingHorizontal: 1/);
  assert.match(programChart, /allocationSegment: \{ borderRadius: 2/);
  assert.match(programChart, /key=\{`\$\{index\}-\$\{label\}`\}/);
  assert.match(programChart, /export function programDailyMetricData/);
  assert.match(programChart, /weeks\.flatMap\(\(week\) => week\.days\.map/);
  assert.match(programChart, /axisLabels = \["S1", "S2"\]/);
  assert.match(programChart, /width <= 780[\s\S]*?\? \{ width: 120 \}/);
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
    "/api/v1/foods/label-captures",
    "/api/v1/subscriptions",
    "/api/v1/subscriptions/apple/transactions",
    "/api/v1/account/disclosures",
    "/api/v1/account/delete",
  ]) {
    assert.ok(schema.paths[route], `missing ${route}`);
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
  assert.equal(screenshots.shots.length, 6);
  assert.match(notes, /App Store Connect/);
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
