import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("in-progress program, plan and meal menus open dedicated information views", async () => {
  const program = await readTestFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  const programActions = await readTestFile(path.resolve(process.cwd(), "src/components/programs/program-active-actions.tsx"), "utf8");
  const day = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id].tsx"), "utf8");
  const meal = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");
  const entityActions = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendarized-entity-actions.tsx"), "utf8");

  assert.match(program, /onOpenInformation=\{\(\) => router\.push\("\/program\/information" as Href\)\}/);
  assert.match(programActions, /label="Ver información del elemento"/);
  assert.match(day, /onOpenInformation=\{\(\) => router\.push\(`\/program\/days\/\$\{day\.id\}\/information` as Href\)\}/);
  assert.doesNotMatch(day, /title="Información del día"/);
  assert.match(meal, /onOpenInformation=\{\(\) => router\.push\(`\/program\/days\/\$\{dayId\}\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/information` as Href\)\}/);
  assert.match(entityActions, /<Text style=\{styles\.actionLabel\}>Ver información del elemento<\/Text>/);
});

test("in-progress information routes preserve the current element hierarchy", async () => {
  const information = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendarized-item-information-screen.tsx"), "utf8");
  const programRoute = await readTestFile(path.resolve(process.cwd(), "src/app/program/information.tsx"), "utf8");
  const dayRoute = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/information/index.tsx"), "utf8");
  const mealRoute = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey]/information/index.tsx"), "utf8");

  assert.match(information, /title: "Información del elemento"/);
  assert.doesNotMatch(information, /forceFallback/);
  assert.match(information, /entity === "program"/);
  assert.match(information, /entity === "dailyPlan"/);
  assert.match(information, /day\.plan_snapshot\?\.meals\?\.find/);
  assert.match(programRoute, /entity="program"/);
  assert.match(dayRoute, /entity="dailyPlan"/);
  assert.match(mealRoute, /entity="meal"/);
});

test("foods opened from an in-progress meal inherit the library information action", async () => {
  const meal = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");
  const libraryDetail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");

  assert.match(meal, /router\.push\(`\/libraries\/foods\/\$\{food\.detailId\}` as Href\)/);
  assert.match(libraryDetail, /onOpenInformation=\{\(\) => router\.push\(`\/libraries\/\$\{entitySlug\}\/\$\{item\.id\}\/information` as Href\)\}/);
});
