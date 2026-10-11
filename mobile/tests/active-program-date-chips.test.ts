import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string) {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("active program dates use slim metadata chips beside their eyebrows", async () => {
  const overview = await source("src/components/programs/program-active-card.tsx");
  const planning = await source("src/components/libraries/program-planning-controls.tsx");

  assert.match(overview, /eyebrow="Programa activo" eyebrowAccessory=\{<HeaderMetadataChip kind="date"/);
  assert.match(overview, /compactDateLabel\(calendarization\.start_date\)/);
  assert.match(overview, /compactDateLabel\(calendarization\.end_date\)/);
  assert.match(planning, /<HeaderMetadataChip kind="date" value=\{detail\} \/>/);
  assert.doesNotMatch(planning, /StructuralIndicators/);
});
