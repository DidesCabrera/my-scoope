import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";


test("Home uses the consolidated read projection", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");

  assert.ok(source.includes('apiRequest<HomeData>("/api/v1/home")'));
  assert.ok(!source.includes("/api/v1/library/programs?limit=1"));
  assert.ok(!source.includes("/api/v1/program/active"));
});

test("library lists start bounded and prefetch the next page near the end", async () => {
  const source = await readFile(
    path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"),
    "utf8",
  );

  assert.ok(source.includes("const INITIAL_PAGE_SIZE = 12"));
  assert.ok(source.includes("distanceFromEnd < 640"));
  assert.ok(source.includes("load({ append: true, offset: page.items.length })"));
});
