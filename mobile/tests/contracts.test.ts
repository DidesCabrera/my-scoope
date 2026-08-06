import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import tokens from "../src/design/tokens.json";

test("mobile visual grammar exposes the reusable card and nutrition tokens", () => {
  assert.equal(tokens.contract, "myscoope.visual-grammar.v1");
  assert.equal(tokens.radius.card, 22);
  assert.equal(tokens.color.surfaceApp, "#000000");
  for (const key of ["protein", "carbs", "fat", "kcalSurface", "food", "meal", "dailyPlan", "program"] as const) {
    assert.match(tokens.color[key], /^#[0-9A-F]{6}$/);
  }
});

test("the committed mobile contract exposes every route consumed through CML05", async () => {
  const file = path.resolve(process.cwd(), "../docs/00_current/api/mobile-v1.openapi.json");
  const schema = JSON.parse(await readFile(file, "utf8")) as { info: { version: string }; paths: Record<string, unknown> };
  assert.equal(schema.info.version, "1.0.0");
  for (const route of [
    "/api/v1/session",
    "/api/v1/sessions/{device_session_id}",
    "/api/v1/me",
    "/api/v1/onboarding",
    "/api/v1/today",
    "/api/v1/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
    "/api/v1/program/active/reminders",
    "/api/v1/program/reviews",
    "/api/v1/program/revisions",
    "/api/v1/program/revisions/{revision_id}/decision",
    "/api/v1/weights",
    "/api/v1/foods/label-captures",
  ]) {
    assert.ok(schema.paths[route], `missing ${route}`);
  }
});
