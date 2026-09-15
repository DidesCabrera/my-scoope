import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("calendarized and pinned plan surfaces normalize legacy meal execution payloads", async () => {
  for (const relativePath of [
    "src/app/program/days/[id].tsx",
    "src/app/program/days/[id]/meals/[mealKey].tsx",
    "src/components/calendarization/meal-adherence-check-in.tsx",
    "src/components/calendarization/calendarized-daily-plan-card.tsx",
    "src/components/calendarization/pinned-daily-plan-card.tsx",
    "src/components/libraries/entity-panels.tsx",
    "src/components/libraries/library-detail-screen.tsx",
  ]) {
    const source = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assertSourceMatch(source, /normalizeMealExecution/);
  }
});

test("route render errors stay inside the app and offer a retry", async () => {
  const layout = await readTestFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");

  assertSourceMatch(layout, /function ScreenErrorBoundary/);
  assertSourceMatch(layout, /unstable_screenErrorBoundary=\{ScreenErrorBoundary\}/);
  assertSourceMatch(layout, /Sentry\.captureException\(error\)/);
  assertSourceMatch(layout, /accessibilityLabel="Reintentar abrir esta vista"/);
});

test("calendarized food preparation refreshes the exact day instead of trusting the generic today payload", async () => {
  for (const relativePath of [
    "src/app/program/days/[id].tsx",
    "src/app/program/days/[id]/meals/[mealKey].tsx",
  ]) {
    const source = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assertSourceMatch(source, /await apiRequest\(`\/api\/v1\/days\//);
    assertSourceMatch(source, /await apiRequest<CalendarizedDayDetail>\(`\/api\/v1\/program\/days\//);
  }
});
