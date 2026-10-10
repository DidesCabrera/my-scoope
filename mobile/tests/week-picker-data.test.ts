import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("new-week flow loads only the created week with a legacy fallback", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/pickers/week-to-program.tsx"), "utf8");

  assert.match(screen, /\/library\/programs\/\$\{targetId\}\/weeks\/\$\{createdWeek\}\/picker-detail/);
  assert.match(screen, /setWeek\(await apiRequest<LibraryWeekPanelItem>/);
  assert.match(screen, /nextError instanceof MobileApiError[^\n]*!\[404, 422\]\.includes\(nextError\.status\)/);
  assert.match(screen, /target\.panel\.weeks\.find\(\(item\) => item\.week_number === createdWeek\)/);
  assert.doesNotMatch(screen, /setTarget\(/);
});
