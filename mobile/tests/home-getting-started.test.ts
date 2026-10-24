import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("Home guides people without a minuta or a commitment after the week and greeting", async () => {
  const home = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");

  assertSourceMatch(home, /apiRequest<CalendarDayDetailData>\(`\/api\/v1\/calendar\/days\/\$\{homeData\.today\.local_date\}`\)/);
  assertSourceMatch(home, /setTodayCommitments\(todayCalendar\?\.commitments \?\? \[\]\)/);
  assertSourceMatch(home, /const showGettingStarted = Boolean\(today && !hasDatedPlan && !today\.calendarization && !today\.pinned_plan && todayCommitments\.length === 0\)/);
  assertSourceMatch(home, /<CurrentWeekSection localDate=\{today\.local_date\} \/>[\s\S]*?style=\{styles\.greetingTitle\}[\s\S]*?showGettingStarted \? \([\s\S]*?<HomeGettingStarted \/>/);
  assertSourceMatch(home, /!showGettingStarted && calendarProgress/);
  assertSourceMatch(home, /!showGettingStarted && today \? <>[\s\S]*?<TodayCommitmentsSectionHeader \/>/);
  assertSourceMatch(home, /<HomeLibraryGrid counts=\{libraryCounts\} \/>[\s\S]*?Accesos rápidos/);
});

test("the getting-started journey teaches the meal to minuta to assignment sequence", async () => {
  const journey = await readTestFile(path.resolve(process.cwd(), "src/components/home/home-getting-started.tsx"), "utf8");

  assertSourceMatch(journey, /Construye tu sistema paso a paso/);
  assertSourceMatch(journey, /Agrega comidas recurrentes[\s\S]*Define minutas recurrentes[\s\S]*Asigna tus minutas/);
  assertSourceMatch(journey, /label: "Explorar comidas"[\s\S]*router\.push\("\/explore\/meals" as Href\)/);
  assertSourceMatch(journey, /label: "Crear desde cero"[\s\S]*entity: "meal"/);
  assertSourceMatch(journey, /label: "Explorar minutas"[\s\S]*router\.push\("\/libraries\/daily-plans" as Href\)/);
  assertSourceMatch(journey, /label: "Armar con mis comidas"[\s\S]*entity: "dailyPlan"/);
  assertSourceMatch(journey, /label: "Agregar al calendario"[\s\S]*router\.push\("\/calendar" as Href\)/);
  assertSourceMatch(journey, /label: "Construir un programa"[\s\S]*entity: "program"/);
  assertSourceDoesNotMatch(journey, /\bIA\b|cr[eé]dito/i);
});

test("the development preview preserves the week and greeting above the journey", async () => {
  const preview = await readTestFile(path.resolve(process.cwd(), "src/app/dev/home-getting-started.tsx"), "utf8");

  assertSourceMatch(preview, /if \(!__DEV__\) return <Redirect href="\/" \/>/);
  assertSourceMatch(preview, /headerShown: true/);
  assertSourceMatch(preview, /<CurrentWeekSection[\s\S]*?💪🏻Vamos Felipe![\s\S]*?<GuideMetric[\s\S]*?88,2 kg[\s\S]*?Fallar en planificar, es planificar fallar[\s\S]*?<HomeGettingStarted \/>[\s\S]*?<HomeLibraryGrid[\s\S]*?Accesos rápidos/);
});
