import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { resetNavigationPressGuard, runGuardedNavigation } from "../src/navigation/navigation-press-guard";
import { assertSourceMatch } from "./support/source-contract";

test.afterEach(() => resetNavigationPressGuard());

test("only the first navigation action runs during a rapid sequence", () => {
  const destinations: string[] = [];

  assert.equal(runGuardedNavigation(() => destinations.push("first")), true);
  assert.equal(runGuardedNavigation(() => destinations.push("second")), false);
  assert.deepEqual(destinations, ["first"]);
});

test("a navigation action can run after the guard resets", () => {
  let navigationCount = 0;

  runGuardedNavigation(() => { navigationCount += 1; });
  resetNavigationPressGuard();
  runGuardedNavigation(() => { navigationCount += 1; });

  assert.equal(navigationCount, 2);
});

test("a failed navigation releases the guard immediately", () => {
  assert.throws(() => runGuardedNavigation(() => { throw new Error("navigation failed"); }), /navigation failed/);

  let navigated = false;
  assert.equal(runGuardedNavigation(() => { navigated = true; }), true);
  assert.equal(navigated, true);
});

test("panel and entity-card links share the navigation press guard", async () => {
  const [panels, product] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/components/ui/product.tsx"), "utf8"),
  ]);

  assertSourceMatch(panels, /onPress=\{\(\) => runGuardedNavigation\(\(\) => onOpenItem\?\.\(item\)\)\}/);
  assertSourceMatch(product, /onPress=\{\(\) => runGuardedNavigation\(headingLink\.onPress\)\}/);
  assertSourceMatch(product, /role === "link" \? runGuardedNavigation\(onPress\) : onPress\(\)/);
});
