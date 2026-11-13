import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("preparation cards expose rename and confirmed delete beside the detail chevron", async () => {
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/preparations/preparation-library-card.tsx"), "utf8");
  const library = await readTestFile(path.resolve(process.cwd(), "src/app/libraries/preparations/index.tsx"), "utf8");
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/preparations/preparation-card-actions.tsx"), "utf8");

  assertSourceMatch(card, /<MoreHorizontal[\s\S]*\{openAction\}/);
  assertSourceMatch(card, /actions=\{actions\}/);
  assertSourceMatch(actions, /label="Renombrar preparación"/);
  assertSourceMatch(actions, /destructive icon=\{Trash2\} label="Eliminar preparación"/);
  assertSourceMatch(library, /item\.is_personal && item\.is_active \? \(\) => \{ setSelected\(item\); setActionsVisible\(true\); \}/);
  assertSourceMatch(library, /\/draft`, \{ method: "PATCH"/);
  assertSourceMatch(library, /method: "PUT"/);
  assertSourceMatch(library, /Alert\.alert\("Eliminar preparación"[\s\S]*method: "DELETE"/);
});
