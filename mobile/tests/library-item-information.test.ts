import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("library details move element metadata into a dedicated action and route", async () => {
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-actions.tsx"), "utf8");
  const information = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-item-information-screen.tsx"), "utf8");

  assert.doesNotMatch(detail, /<EntityDetailMetadata/);
  assert.match(detail, /action: item \? \{ label: `Más acciones para \$\{item\.name\}`/);
  assert.match(detail, /onOpenInformation=\{\(\) => router\.push\(`\/libraries\/\$\{entitySlug\}\/\$\{item\.id\}\/information` as Href\)\}/);
  assert.match(actions, /<Text style=\{styles\.actionLabel\}>Ver información del elemento<\/Text>/);
  assert.match(actions, /<Info color=\{tokens\.color\.textMain\}/);
  assert.match(information, /title: "Información del elemento"/);
  assert.doesNotMatch(information, /forceFallback/);
  assert.match(information, /<EntityDetailMetadata creator=\{item\.creator\} updatedAt=\{libraryDate\(item\.created_at\)\} \/>/);
});

test("every library entity exposes its information route", async () => {
  const routes = [
    ["foods", "Food"],
    ["meals", "Meal"],
    ["daily-plans", "DailyPlan"],
    ["programs", "Program"],
  ] as const;

  for (const [slug, name] of routes) {
    const route = await readTestFile(path.resolve(process.cwd(), `src/app/libraries/${slug}/[id]/information.tsx`), "utf8");
    assert.match(route, new RegExp(`export default function ${name}InformationScreen`));
    assert.match(route, new RegExp(`entitySlug="${slug}"`));
  }
});
