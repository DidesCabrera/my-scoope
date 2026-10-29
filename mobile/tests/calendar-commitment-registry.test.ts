import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import type { CalendarCommitment, CalendarDay } from "../src/api/calendar-types";
import { commitmentsForMonth } from "../src/components/calendarization/calendar-commitment-registry";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

function day(date: string, kind: CalendarCommitment["kind"]): CalendarDay {
  return {
    calendar_date: date, commitments: [{ id: Number(date.slice(-2)), calendar_date: date, kind, note: "", food_period_start: null, food_period_end: null, food_plans_count: 0, foods: [] }],
    has_execution: false, has_plan: false, id: null, plan_name: "", source_kind: null, source_program_name: null,
  };
}

test("monthly commitment tabs keep the full month and include today in upcoming", () => {
  const days = [day("2026-09-30", "cooking"), day("2026-10-20", "shopping"), day("2026-10-27", "cooking"), day("2026-10-31", "training"), day("2026-11-01", "nutritionist")];
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "upcoming").map((item) => item.calendar_date), ["2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "all").map((item) => item.calendar_date), ["2026-10-20", "2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "cooking", "upcoming").map((item) => item.calendar_date), ["2026-10-27"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-09", "2026-10-27", "all", "upcoming"), []);
});

test("calendar and commitment registry share the reduced top spacing", async () => {
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-month-calendar.tsx"), "utf8");
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(calendar, /export const calendarTopSpacing = -24;/);
  assertSourceMatch(calendar, /calendarSection: \{ marginBottom: 12, marginTop: calendarTopSpacing, paddingVertical: tokens\.spacing\.sm \}/);
  assertSourceMatch(registry, /calendarSection: \{ marginTop: calendarTopSpacing, paddingVertical: tokens\.spacing\.sm \}/);
});

test("calendar views present the month calendar before the selected day", async () => {
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(calendar, /<CalendarMonthCalendar[\s\S]*<View style=\{styles\.todaySection\}>/);
  assertSourceMatch(calendar, /todaySection: \{ gap: tokens\.spacing\.sm, marginTop: 8 \}/);
  assertSourceMatch(calendar, /<CalendarMonthCalendar[\s\S]*label="Añadir minuta"[\s\S]*setPlanMenuVisible\(true\)[\s\S]*label="Añadir compromiso"[\s\S]*setCommitmentMenuVisible\(true\)[\s\S]*<View style=\{styles\.todaySection\}>/);
  assertSourceMatch(registry, /<View style=\{styles\.calendarSection\}>[\s\S]*<CommitmentDayPreview/);
});

test("calendar day headings show today as a multicolor chip beside the full date", async () => {
  const heading = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-day-section-heading.tsx"), "utf8");
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  assertSourceMatch(heading, /function TodayChip[\s\S]*LinearGradient[\s\S]*tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat[\s\S]*>Hoy<\/Text>[\s\S]*isToday \? <TodayChip \/>[\s\S]*readableDate\(date\)/);
  assertSourceMatch(registry, /<CalendarDaySectionHeading date=\{date\} today=\{today\} \/>/);
  assertSourceMatch(calendar, /<CalendarDaySectionHeading date=\{selectedCalendarDate\} today=\{overview\.local_date\} \/>/);
});

test("past commitment dots use fifty percent opacity across calendars", async () => {
  for (const relativePath of [
    "src/components/calendarization/calendar-month-calendar.tsx",
    "src/components/calendarization/calendar-select-plans-screen.tsx",
    "src/components/calendarization/current-week-section.tsx",
    "src/app/calendar/registry.tsx",
    "src/app/calendar/commitments.tsx",
    "src/app/calendar/commitments/[id].tsx",
  ]) {
    const source = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(source, /commitmentDotsPast: \{ opacity: 0\.5 \}|gridCommitmentDotsPast: \{ opacity: 0\.5 \}/, relativePath);
  }
});

test("calendar entry uses a full-screen loading state", async () => {
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  assertSourceMatch(calendar, /if \(loading && !overview\) return <LoadingState label=\{extended \? "Preparando tus próximas minutas…" : "Preparando tu calendario…"\} \/>/);
});

test("commitment registry entry uses a full-screen loading state", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(registry, /if \(loading && !overview\) return <LoadingState label="Preparando tus compromisos…" \/>/);
});

test("commitment registration actions use their semantic icon colors", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  const actionSheet = await readTestFile(path.resolve(process.cwd(), "src/components/ui/action-sheet-modal.tsx"), "utf8");
  assertSourceMatch(registry, /iconBackgroundColor=\{`\$\{commitmentPresentation\[kind\]\.color\}33`\}/);
  assertSourceMatch(registry, /iconColor=\{commitmentPresentation\[kind\]\.color\}/);
  assertSourceMatch(actionSheet, /actionIconColored: \{ borderRadius: 10, height: 32, width: 32 \}/);
});

test("commitment registration marks today with the multicolor outline", async () => {
  const registration = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/commitments.tsx"), "utf8");
  assertSourceMatch(registration, /day\.calendar_date === localToday \? <CalendarTodayOutline \{\.\.\.todaySize\} \/>/);
  assertSourceMatch(registration, /onLayout=\{day\.calendar_date === localToday/);
  assertSourceMatch(registration, /gridDateToday: \{ borderWidth: 0 \}/);
});

test("commitment registration actions use concise labels", async () => {
  const commitments = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-commitments.ts"), "utf8");
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(commitments, /shopping: "Compras",[\s\S]*cooking: "Cocinar",[\s\S]*training: "Entrenamiento"/);
  assertSourceMatch(registry, /label=\{commitmentActionLabel\[kind\]\}/);
});

test("commitment registration popup uses a pin as its main icon", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(registry, /icon=\{Pin\} onClose=\{\(\) => setMenuVisible\(false\)\} title="Registrar compromiso"/);
});

test("commitment registry header summarizes upcoming commitments by type", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  const commitments = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-commitments.ts"), "utf8");
  assertSourceMatch(registry, /Próximos compromisos agendados por tipo[\s\S]*commitmentKinds\.map[\s\S]*upcomingCounts\[kind\][\s\S]*commitmentActionLabel\[kind\]/);
  assertSourceMatch(registry, /const visibleUpcomingCommitmentCounts = useMemo[\s\S]*day\.calendar_date < localToday[\s\S]*counts\[commitment\.kind\] \+= 1/);
  assertSourceMatch(registry, /overview\?\.future_commitments_count_by_kind \?\? visibleUpcomingCommitmentCounts/);
  assertSourceMatch(registry, /<CommitmentHeader onOpenRegistration=\{openRegistration\} upcomingCounts=\{upcomingCommitmentCounts\} \/>/);
  assertSourceMatch(registry, /accessibilityRole="button"[\s\S]*onPress=\{\(\) => onOpenRegistration\(kind\)\}/);
  assertSourceMatch(registry, /headerDashboardMetricValueRow: \{ alignItems: "center", flexDirection: "row", gap: tokens\.spacing\.xs \}/);
  assertSourceMatch(registry, /styles\.headerDashboardMetric, \{ backgroundColor: `\$\{presentation\.color\}33` \}/);
  assertSourceMatch(registry, /headerDashboard: \{ flexDirection: "row", gap: tokens\.spacing\.xs, marginBottom: 4, marginHorizontal: -6, marginTop: tokens\.spacing\.xs \+ 4 \}/);
  assertSourceMatch(registry, /headerDashboardMetric: \{[^}]*paddingVertical: tokens\.spacing\.sm \+ 4[^}]*\}/);
  assertSourceDoesNotMatch(`${registry}\n${commitments}`, /Cita nutricionista/);
  assertSourceMatch(commitments, /nutritionist: \{ label: "Nutricionista"/);
  assertSourceMatch(registry, /<Pin accessibilityLabel="Mis compromisos" color=\{tokens\.color\.textMain\} size=\{28\} strokeWidth=\{2\.1\} \/>/);
  assertSourceMatch(registry, /mainIcon: \{ paddingVertical: 4 \}/);
  assertSourceDoesNotMatch(registry, /styles\.headerIcons/);
  assertSourceMatch(registry, />Próximos compromisos<\/Text>/);
  assertSourceMatch(registry, />Calendario mis compromisos<\/Text>[\s\S]*<CommitmentHeader onOpenRegistration=\{openRegistration\} upcomingCounts=\{upcomingCommitmentCounts\} \/>[\s\S]*<ScrollableTabBar/);
  assertSourceMatch(registry, /styles\.headerDashboardHeading[\s\S]*<Clock[^>]*>[\s\S]*Próximos compromisos/);
  assertSourceMatch(registry, /styles\.calendarTabsHeading[\s\S]*<CalendarDays[^>]*>[\s\S]*Calendario mis compromisos/);
});

test("commitment filter tabs show their semantic icons without icon backgrounds", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  assertSourceMatch(registry, /icon: \(selected: boolean\) => <Icon color=\{selected \? tokens\.color\.surfaceApp : presentation\.color\} size=\{14\} strokeWidth=\{2\.1\} \/>/);
});

test("calendar overview presents commitments as an actionable mini card", async () => {
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  assertSourceMatch(calendar, /Próximos compromisos[\s\S]*futurePlansCount[\s\S]*commitmentKinds\.map[\s\S]*futureCommitmentCounts\[kind\]/);
  assertSourceMatch(calendar, /upcomingCommitmentsDashboard: \{ flexDirection: "row", gap: tokens\.spacing\.xs, marginHorizontal: -6 \}/);
  assertSourceMatch(calendar, /upcomingCommitmentsIcon[\s\S]*upcomingCommitmentsValue/);
  assertSourceDoesNotMatch(calendar, /upcomingCommitmentsLabel/);
  assertSourceMatch(calendar, /calendarBlock: \{ gap: 0, marginTop: 18 \}/);
  assertSourceMatch(calendar, /<ProgramSectionHeader icon=\{CalendarClock\} title="Resumen minutas y compromisos" \/>[\s\S]*<View style=\{styles\.calendarizeActions\}>/);
  assertSourceMatch(calendar, /<Card style=\{styles\.commitmentsCard\}>[\s\S]*<Pin[^>]*>[\s\S]*Mis compromisos[\s\S]*commitmentKinds\.map[\s\S]*accessibilityLabel="Agregar nuevo compromiso"[\s\S]*<Plus[^>]*>[\s\S]*accessibilityLabel="Ver compromisos"[\s\S]*Ver compromisos[\s\S]*<ChevronRight/);
  assertSourceMatch(calendar, /commitmentsCardIcon: \{ alignItems: "center", borderRadius: 8, height: 24, justifyContent: "center", width: 24 \}/);
  assertSourceMatch(calendar, /commitmentsCardIcons: \{ flexDirection: "row", gap: 5 \}/);
  assertSourceMatch(calendar, /commitmentsCardActionChip: \{[^}]*height: 40[^}]*paddingHorizontal: tokens\.spacing\.md[^}]*\}/);
  assertSourceMatch(calendar, /commitmentsCardAddButton: \{ borderRadius: 20, paddingHorizontal: 0, width: 40 \}/);
  assertSourceMatch(calendar, /commitmentsCardActions: \{ alignItems: "center", flexDirection: "row", gap: tokens\.spacing\.sm, justifyContent: "space-between", marginHorizontal: -6, marginTop: 8 \}/);
  assertSourceMatch(calendar, /commitmentsCard: \{ gap: tokens\.spacing\.sm, marginHorizontal: -12, paddingBottom: tokens\.card\.outerPadding - 6, paddingTop: tokens\.card\.outerPadding - 4 \}/);
  assertSourceMatch(calendar, /commitmentsCardOverview: \{ alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between" \}/);
  assertSourceMatch(calendar, /styles\.commitmentsCardActionChip[\s\S]*styles\.commitmentsCardActionChip/);
  assertSourceMatch(calendar, /visible=\{commitmentMenuVisible\}[\s\S]*title="Registrar compromiso"[\s\S]*label=\{commitmentActionLabel\[kind\]\}/);
  assertSourceMatch(calendar, /Compromisos asignados[\s\S]*Última fecha con compromiso[\s\S]*Próximo compromiso[\s\S]*nextAssignedCommitment/);
  assertSourceMatch(calendar, /Próximo compromiso<\/Text>[\s\S]*styles\.planningNextPlanEntity[\s\S]*nextAssignedCommitment/);
  assertSourceDoesNotMatch(calendar, /commitmentsCardSubtitle/);
});

test("commitment registry cards expose food list creation and attached list details", async () => {
  const registry = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/registry.tsx"), "utf8");
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-commitment-list-card.tsx"), "utf8");
  assertSourceMatch(registry, /onCreateFoodList=\{\(\) => router\.push\(`\/calendar\/commitments\/\$\{commitment\.id\}\/foods\?date=\$\{commitment\.calendar_date\}`/);
  assertSourceMatch(registry, /showFoodListDetails/);
  assertSourceMatch(card, /commitmentSupportsFoods\(commitment\.kind\)[\s\S]*Crear lista de alimentos/);
  assertSourceMatch(card, /Lista de alimentos adjunta[\s\S]*commitment\.foods\.length[\s\S]*commitment\.food_plans_count[\s\S]*calendarFoodPeriodDayCount/);
});

test("calendar overview presents planning as an actionable mini card", async () => {
  const calendar = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  assertSourceMatch(calendar, /<CalendarClock[^>]*>[\s\S]*Minutas programadas[\s\S]*styles\.commitmentsCardIcon[\s\S]*<ClipboardList[^>]*size=\{14\}[\s\S]*styles\.commitmentsCardIcon[\s\S]*<ChartNoAxesCombined[^>]*size=\{14\}[\s\S]*accessibilityLabel="Calendarizar"[\s\S]*<Plus[^>]*>[\s\S]*Ver minutas programadas/);
  assertSourceMatch(calendar, /visible=\{planMenuVisible\}[\s\S]*label="Calendarizar minuta"[\s\S]*label="Calendarizar programa"/);
  assertSourceMatch(calendar, /onPress=\{\(\) => router\.push\("\/calendar\/plans" as Href\)\}[\s\S]*Ver minutas programadas/);
  assertSourceMatch(calendar, /styles\.planningSummary[\s\S]*Planes programados[\s\S]*Última fecha con plan[\s\S]*Próxima minuta[\s\S]*nextScheduledPlan\?\.plan_name/);
  assertSourceMatch(calendar, /Próxima minuta<\/Text>[\s\S]*styles\.planningNextPlanEntity[\s\S]*<EntityIcon entity="dailyPlan"/);
  assertSourceMatch(calendar, /planningNextPlanCopy: \{ alignItems: "center", flex: 1, flexDirection: "row", gap: tokens\.spacing\.sm, justifyContent: "space-between" \}/);
  assertSourceMatch(calendar, /planningNextPlanDate: \{ color: tokens\.color\.textMain, fontSize: 12, fontWeight: tokens\.weight\.semibold \}/);
  assertSourceMatch(calendar, /planningSummary: \{[^}]*borderRadius: tokens\.radius\.lg[^}]*marginTop: 4[^}]*padding: tokens\.spacing\.sm \+ 6[^}]*\}/);
  assertSourceMatch(calendar, /const nextScheduledPlan = useMemo/);
  assertSourceDoesNotMatch(calendar, /styles\.summaryRow/);
});

test("scheduled plans view reuses the upcoming minutes section with a selected system plan card", async () => {
  const plans = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/plans.tsx"), "utf8");
  assertSourceMatch(plans, /title="Mis minutas programadas"/);
  assertSourceMatch(plans, /<SectionPageHeader icon=\{<Pin color=\{tokens\.color\.textMain\}/);
  assertSourceMatch(plans, /Calendario de minutas/);
  assertSourceMatch(plans, /const monthDays = useMemo\(\(\) => overview\?\.days \?\? \[\], \[overview\]\)/);
  assertSourceMatch(plans, /<CalendarMonthCalendar[\s\S]*<CalendarDaySectionHeading/);
  assertSourceMatch(plans, /futurePlansCount[\s\S]*Minutas programadas/);
  assertSourceDoesNotMatch(plans, /Resumen de minutas/);
  assertSourceMatch(plans, /<CalendarizedDailyPlanCard[\s\S]*snapshot=\{detail\.plan_snapshot\}/);
  assertSourceMatch(plans, /<ProgramSectionHeader icon=\{CalendarDays\} subtitle="Los próximos siete días, con o sin plan asignado\." title="Próximas minutas"/);
  assertSourceMatch(plans, /<CalendarWeekMetrics days=\{upcoming\}/);
  assertSourceMatch(plans, /<CalendarUpcomingPanels[\s\S]*days=\{upcoming\}/);
  assertSourceMatch(plans, /<Button label="Ver más fechas" onPress=\{\(\) => router\.push\("\/calendar\/future" as Href\)\} variant="secondary" \/>/);
  assertSourceMatch(plans, /<ClipboardList color=\{tokens\.color\.entityIconForeground\}/);
  assertSourceMatch(plans, /summaryIcon: \{[^}]*backgroundColor: tokens\.color\.dailyPlan/);
  assertSourceDoesNotMatch(plans, /Minutas de \$\{visibleMonth/);
  assertSourceDoesNotMatch(plans, /label: "Próximas"[\s\S]*label: "Todas"/);
});
