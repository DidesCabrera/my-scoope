import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import {
  applyComparatorSelection,
  initialComparisonSlots,
} from "../src/components/comparisons/comparison-state";
import { assertSourceDoesNotMatch, assertSourceMatch } from "./support/source-contract";

test("comparison builder starts with two independent empty slots", () => {
  const slots = initialComparisonSlots();

  assert.deepEqual(slots, [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ]);
  assert.notEqual(slots[0], slots[1]);
});

test("saved comparison results omit the explanatory snapshot notice", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceDoesNotMatch(source, /fotografía guardada|historical_snapshot|InlineNotice/);
  assertSourceMatch(source, /<SectionHeading icon=\{<Scale color=\{tokens\.color\.entityIconForeground\} size=\{18\} \/>\} title="Resultados comparativos" \/>/);
  assertSourceDoesNotMatch(source, /SectionTitle/);
});

test("comparison builder separates its generated results from the controls", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  assertSourceMatch(source, /<SectionDivider \/>[\s\S]*<ComparisonResultCards result=\{result\} \/>/);
});

test("comparison result rows omit numeric position badges", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceDoesNotMatch(source, /positionBadge|positionText|>\{bar\.position\}<\/Text>/);
});

test("comparison percentage bars match the compact progress height", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");
  assertSourceMatch(source, /track: \{[^}]*borderRadius: tokens\.radius\.pill[^}]*height: 10/);
});

test("saved comparison detail switches between result cards and entity cards", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  assertSourceMatch(source, /<DistributedTabBar<DetailTab>/);
  assertSourceMatch(source, /<View style=\{styles\.tabsBleed\}>[\s\S]*<DistributedTabBar<DetailTab>/);
  assertSourceMatch(source, /tabsBleed: \{ alignSelf: "stretch", marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  assertSourceMatch(source, /scrollHeader=\{<AppHeader/);
  assertSourceMatch(source, /stickyHeader=\{<View style=\{styles\.tabsBleed\}>/);
  assertSourceMatch(source, /onHeaderVisibilityChange=\{setCompactHeaderVisible\}/);
  assertSourceMatch(source, /identityVisible: compactHeaderVisible/);
  assertSourceMatch(source, /`Comparación \$\{entityTabLabels\[comparison\.kind\]\}`/);
  assertSourceMatch(source, /action: comparisonId != null \? \{ icon: "more", label: "Acciones de comparación"/);
  assertSourceMatch(source, /<SavedComparisonActions/);
  assertSourceDoesNotMatch(source, /<Button[^>]*label="Editar comparación"|Usar en el Asistente|Volver a guardadas/);
  assertSourceMatch(source, /key: "cards", label: "Cards"/);
  assertSourceMatch(source, /label: entityTabLabels\[kind\]/);
  assertSourceMatch(source, /activeTab === "cards" \? <ComparisonResultCards/);
  assertSourceMatch(source, /Promise\.all\(saved\.items\.map\(\(item\) => apiRequest<LibraryItem>/);
  assertSourceMatch(source, /activeTab === "entities" \? entityItems\.map/);
  assertSourceMatch(source, /<LibraryCard apiRequest=\{apiRequest\} interactive=\{false\} item=\{item\}[^>]*navigable/);
});

test("picker result updates only its destination without mutating prior state", () => {
  const original = initialComparisonSlots();
  const option = { id: 42, name: "Avena" };

  const updated = applyComparatorSelection(original, { slotKey: 2, option });

  assert.equal(original[1]?.option, null);
  assert.equal(updated[0], original[0]);
  assert.deepEqual(updated[1], { key: 2, option, quantity: "100" });
});

test("stale picker result leaves slots unchanged", () => {
  const original = initialComparisonSlots();

  const updated = applyComparatorSelection(original, {
    slotKey: 999,
    option: { id: 7, name: "Arroz" },
  });

  assert.deepEqual(updated, original);
});
