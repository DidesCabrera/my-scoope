import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import type { CalendarOverviewData } from "../src/api/calendar-types";
import { emptyDaySituation } from "../src/components/home/home-empty-day";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("Home guides people without a minuta even when they have a calendarization or commitment", async () => {
  const home = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");

  assertSourceMatch(home, /apiRequest<CalendarDayDetailData>\(`\/api\/v1\/calendar\/days\/\$\{homeData\.today\.local_date\}`\)/);
  assertSourceMatch(home, /setTodayCommitments\(todayCalendar\?\.commitments \?\? \[\]\)/);
  assertSourceMatch(home, /const showGettingStarted = Boolean\(today && !hasDatedPlan && !today\.pinned_plan\)/);
  assertSourceDoesNotMatch(home, /Programa en curso/);
  assertSourceDoesNotMatch(home, /Tendencia del programa|styles\.measurementRow|styles\.measurementValue/);
  assertSourceMatch(home, /<HomeEmptyDayNotice localDate=\{today\.local_date\} situation=\{emptyDaySituation\(upcomingOverview, today\.local_date\)\} \/>[\s\S]*?\{todayCommitments\.length \|\| commitmentsError \? commitmentsSection : null\}[\s\S]*?<HomeGettingStarted compactTop \/>[\s\S]*?\{calendarSection\}/);
  assertSourceMatch(home, /const calendarSection = visibleMonth && today \? <View style=\{styles\.homeCalendarSection\}>[\s\S]*?title="Tu calendario"/);
  assertSourceMatch(home, /<Card style=\{styles\.homeCalendarCard\}>\s*<CalendarMonthCalendar[\s\S]*?embedded[\s\S]*?<Pressable accessibilityLabel="Ver calendario"[\s\S]*?styles\.homeActionChip[\s\S]*?<\/Card>/);
  assertSourceMatch(home, /homeCalendarCard: \{ gap: 24 \}/);
  assertSourceMatch(home, /title="Tu calendario"\s+variant="home"/);
  assertSourceMatch(home, /<ProgramSectionHeader\s+bottomSpacing=\{24\}\s+icon=\{CalendarDays\}/);
  assertSourceMatch(home, /title="Progreso"\s+variant="home"/);
  assertSourceMatch(home, /icon=\{ChartColumnIncreasing\}[\s\S]*?title="Progreso"/);
  assertSourceMatch(home, /subtitle="Tu elijes cuando partir\. Elije la fecha de inicio de tu progreso cuando te sientas comprometido"/);
  assertSourceMatch(home, /detail=\{<Chip backgroundColor=\{`\$\{tokens\.color\.protein\}1A`\} borderColor=\{tokens\.color\.protein\} label=\{`Inicio el/);
  assertSourceMatch(home, /!showGettingStarted \? calendarSection : null/);
  assertSourceMatch(home, /\{calendarProgress \? <View style=\{styles\.homeProgressSection\}>/);
  assertSourceMatch(home, /!showGettingStarted && today \? commitmentsSection : null/);
  assertSourceMatch(home, /function TodayCommitmentsSection\([\s\S]*?<TodayCommitmentsSectionHeader \/>[\s\S]*?<TodayCommitmentCard/);
  assertSourceMatch(home, /<HomeLibraryGrid counts=\{libraryCounts\} \/>[\s\S]*?Accesos rápidos/);
});

test("the empty-day notice prioritizes future minutas, then the nearest commitment", () => {
  const commitment = { id: 7, calendar_date: "2026-11-02", kind: "training", note: "", food_period_start: null, food_period_end: null, food_plans_count: 0, foods: [] } as const;
  const overview = {
    local_date: "2026-10-26", start_date: "2026-10-26", end_date: "2026-12-06",
    future_plans_count: 1,
    days: [
      { calendar_date: "2026-11-02", commitments: [commitment], has_plan: true },
      { calendar_date: "2026-10-30", commitments: [{ ...commitment, id: 8, calendar_date: "2026-10-30" }], has_plan: true },
    ],
  } as unknown as CalendarOverviewData;
  assert.deepEqual(emptyDaySituation(overview, overview.local_date), { kind: "planned", scheduledPlanDate: "2026-10-30", plansCount: 1 });
  assert.deepEqual(emptyDaySituation({ ...overview, days: [], last_scheduled_date: "2027-01-10" }, overview.local_date), {
    kind: "planned", scheduledPlanDate: "2027-01-10", plansCount: 1,
  });
  assert.deepEqual(emptyDaySituation({ ...overview, days: [], future_plans_count: 2, last_scheduled_date: "2027-01-10" }, overview.local_date), {
    kind: "planned", scheduledPlanDate: "2027-01-10", plansCount: 2,
  });
  assert.deepEqual(emptyDaySituation({ ...overview, future_plans_count: 0 }, overview.local_date), {
    kind: "commitment", commitment: { ...commitment, id: 8, calendar_date: "2026-10-30" },
  });
  assert.equal(emptyDaySituation({ ...overview, future_plans_count: 0, days: [] }, overview.local_date).kind, "empty");
  assert.equal(emptyDaySituation(null, overview.local_date).kind, "unknown");
});

test("Home offers the two library cards without a separate assignment card", async () => {
  const journey = await readTestFile(path.resolve(process.cwd(), "src/components/home/home-getting-started.tsx"), "utf8");

  assertSourceMatch(journey, /Enriquece tus librerías/);
  assertSourceMatch(journey, /<LibraryBig color=\{tokens\.color\.textMain\} size=\{25\} strokeWidth=\{2\.2\} \/>[\s\S]*?Enriquece tus librerías/);
  assertSourceMatch(journey, /introduction: \{ marginTop: 28 \}/);
  assertSourceDoesNotMatch(journey, /Guarda tus comidas habituales|styles\.subtitle/);
  assertSourceMatch(journey, /eyebrow="Mi librería de comidas"[\s\S]*Agrega comidas recurrentes[\s\S]*eyebrow="Mi librería de minutas"[\s\S]*Define minutas reutilizables/);
  assertSourceMatch(journey, /imageSource=\{require\("\.\.\/\.\.\/\.\.\/assets\/images\/home-meals-bowl\.png"\)\}[\s\S]*imageSource=\{require\("\.\.\/\.\.\/\.\.\/assets\/images\/home-daily-plans-containers\.png"\)\}/);
  assertSourceMatch(journey, /<View style=\{styles\.cardBody\}>[\s\S]*?<Image accessible=\{false\} resizeMode="contain" source=\{imageSource\} style=\{\[styles\.illustration, imageStyle\]\} \/>[\s\S]*?<View style=\{styles\.actions\}>/);
  assertSourceMatch(journey, /imageStyle=\{styles\.mealIllustration\}[\s\S]*imageStyle=\{styles\.dailyPlanIllustration\}/);
  assertSourceMatch(journey, /mealIllustration: \{ transform: \[\{ translateX: -18 \}, \{ translateY: -4 \}\] \}/);
  assertSourceMatch(journey, /dailyPlanIllustration: \{ transform: \[\{ scale: 1\.15 \}, \{ translateX: -2 \}, \{ translateY: -4 \}\] \}/);
  assertSourceMatch(journey, /gradientSource=\{require\("\.\.\/\.\.\/\.\.\/assets\/images\/home-meals-gradient-25-17\.png"\)\}[\s\S]*gradientSource=\{require\("\.\.\/\.\.\/\.\.\/assets\/images\/home-daily-plans-gradient-25-17\.png"\)\}/);
  assertSourceMatch(journey, /<Image accessible=\{false\} resizeMode="stretch" source=\{gradientSource\} style=\{\[styles\.gradient, cardSize\]\} \/>/);
  assertSourceMatch(journey, /<Pressable accessibilityLabel=\{label\} accessibilityRole="button" hitSlop=\{6\}[\s\S]*?<ActionIcon color=\{tokens\.color\.entityIconForeground\} size=\{16\}[\s\S]*?<Text style=\{styles\.actionLabel\}>\{label\}<\/Text>/);
  assertSourceMatch(journey, /actionLabel: \{ color: tokens\.color\.entityIconForeground, fontSize: 13/);
  assertSourceMatch(journey, /cardBody: \{ alignItems: "flex-end"/);
  assertSourceMatch(journey, /action: \{[^}]*alignSelf: "flex-end"[^}]*borderRadius: 999, borderWidth: 1[^}]*minHeight: 34, paddingHorizontal: 12/);
  assertSourceMatch(journey, /style=\{\(\{ pressed \}\) => \[styles\.action, \{ borderColor: accent \}/);
  assertSourceDoesNotMatch(journey, /<Button|action: \{[^}]*backgroundColor/);
  assertSourceDoesNotMatch(journey, /description=|styles\.description|<Card accent=\{accent\}>/);
  assertSourceMatch(journey, /label: "Explorar comidas"[\s\S]*router\.push\("\/explore\/meals" as Href\)/);
  assertSourceMatch(journey, /label: "Crear desde cero"[\s\S]*entity: "meal"/);
  assertSourceMatch(journey, /label: "Explorar minutas"[\s\S]*router\.push\("\/explore\/daily-plans" as Href\)/);
  assertSourceMatch(journey, /label: "Armar con mis comidas"[\s\S]*entity: "dailyPlan"/);
  assertSourceDoesNotMatch(journey, /PASO \$\{step\}|Asigna tus minutas|label: "Agregar al calendario"|label: "Construir un programa"/);
  assertSourceDoesNotMatch(journey, /\bIA\b|cr[eé]dito/i);
});

test("the old development preview redirects to the real Home", async () => {
  const preview = await readTestFile(path.resolve(process.cwd(), "src/app/dev/home-getting-started.tsx"), "utf8");

  assertSourceMatch(preview, /return <Redirect href="\/today" \/>/);
  assertSourceDoesNotMatch(preview, /<HomeGettingStarted|CalendarMonthCalendar|Fallar en planificar/);
});
