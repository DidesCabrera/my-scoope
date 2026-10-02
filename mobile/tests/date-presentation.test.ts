import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { formatCompactDate } from "../src/presentation/date";

test("shared card dates use the compact Spanish display format", () => {
  assert.equal(formatCompactDate("2026-09-26T12:00:00-03:00"), "26 sep. 2026");
  assert.equal(formatCompactDate(null), null);
  assert.equal(formatCompactDate("not-a-date"), null);
});

test("assistant cards expose semantic eyebrows and keep dates below titles", async () => {
  const assistant = await readFile(path.resolve(process.cwd(), "src/app/assistant/index.tsx"), "utf8");
  assert.match(assistant, /<MessageCircle color=\{tokens\.color\.textMain\} size=\{16\} strokeWidth=\{2\} \/>[\s\S]*<Text style=\{styles\.eyebrow\}>Chat<\/Text>[\s\S]*\{chat\.title\}[\s\S]*formatCompactDate\(chat\.updated_at\)/);
  assert.match(assistant, /<SectionIcon section="proposal" size="compact" \/>[\s\S]*<Text style=\{styles\.eyebrow\}>Propuesta<\/Text>[\s\S]*\{proposal\.title\}[\s\S]*displayDate\(proposal\.created_at\)/);
  assert.doesNotMatch(assistant, /proposal\.source\.toUpperCase|timeStyle: "short"/);
  assert.doesNotMatch(assistant, /<Pill[^>]*(chat\.status_label|proposal\.status_label)/);
});

test("received cards and proposal detail reuse the shared date format", async () => {
  const inbox = await readFile(path.resolve(process.cwd(), "src/app/inbox.tsx"), "utf8");
  const detail = await readFile(path.resolve(process.cwd(), "src/app/proposals/[id].tsx"), "utf8");
  assert.match(inbox, /\$\{item\.sender\} · \$\{formatCompactDate\(item\.created_at\)/);
  assert.match(detail, /return date \? `Recibida \$\{date\}`/);
});
