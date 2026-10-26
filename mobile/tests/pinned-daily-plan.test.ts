import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("Home creates a dated snapshot while retaining legacy pinned-plan fallback", async () => {
  const home = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/pinned-daily-plan-card.tsx"), "utf8");

  assertSourceMatch(home, /<HomeGettingStarted compactTop=\{Boolean\(planContext \|\| todayCommitments\.length\)\} \/>[\s\S]*Completa tu día/);
  assertSourceMatch(home, /label="Crear un plan para hoy"/);
  assertSourceMatch(home, /apiRequest<CalendarDayDetailData>\(`\/api\/v1\/calendar\/days\/\$\{today\.local_date\}\/plan\/draft`/);
  assertSourceMatch(home, /assignment_key: Crypto\.randomUUID\(\)/);
  assertSourceMatch(home, /<PinnedDailyPlanCard apiRequest=\{apiRequest\} editing=\{pinnedMealEditing\} item=\{today\.pinned_plan\}/);
  assertSourceMatch(home, /onToggleCompleted: \(meal, completed\) => \{ void toggleTodayMealCompletion\(meal\.id, completed, "calendarized"\); \}/);
  assertSourceMatch(home, /onToggleCompleted: \(meal, completed\) => \{ void toggleTodayMealCompletion\(meal\.id, completed, "pinned"\); \}/);
  assertSourceMatch(home, /`\/api\/v1\/days\/\$\{todayDayId\}\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/check-ins`/);
  assertSourceMatch(home, /`\/api\/v1\/today\/pinned-plan\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/check-ins`/);
  assertSourceMatch(home, /setToday\(optimisticMealExecution\(today, mealKey, completed\)\)/);
  assertSourceMatch(home, /apiRequest<CalendarProgressData>\("\/api\/v1\/calendar\/progress"\)/);
  assertSourceMatch(home, /setToday\(previousToday\);/);
  assertSourceMatch(card, /<EntityCard actions=\{detailAction\} entity="dailyPlan" eyebrow="PLAN DEL DÍA" headingLink=\{\{ label: "Ir al detalle del plan", onPress: openDetail \}\} indicators=\{indicators\} title=\{item\.name\}>/);
  assertSourceMatch(card, /label="Ir al detalle del plan"/);
  assertSourceMatch(card, /router\.push\(`\/libraries\/daily-plans\/\$\{item\.id\}` as Href\)/);
  assertSourceMatch(card, /addMealAction: \{ marginTop: tokens\.spacing\.md \}/);
  assertSourceMatch(card, /label="\+ Agregar Comida"/);
  assertSourceMatch(card, /\{ icon: "meal" as const, label: "comidas", value: meals\.length \}/);
  assertSourceMatch(card, /\{ icon: "food" as const, label: "alimentos", value: meals\.reduce/);
});

test("library plans assign dated snapshots and retain legacy pinned completion controls", async () => {
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const cards = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"), "utf8");
  const adherence = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"), "utf8");

  assertSourceMatch(detail, /Asignar al calendario de hoy/);
  assertSourceMatch(detail, /`\/api\/v1\/calendar\/days\/\$\{todayContext\.local_date\}\/plan`/);
  assertSourceMatch(detail, /<DailyMealCompletionCard/);
  assertSourceMatch(detail, /pinnedTracking=\{isPinnedPlan/);
  assertSourceMatch(cards, /<MealCompletionToggleCard/);
  assertSourceMatch(cards, /preparation=\{pinnedTracking/);
  assertSourceMatch(adherence, /mode === "pinned"/);
  assertSourceMatch(adherence, /\/api\/v1\/today\/pinned-plan\/meals/);
});
