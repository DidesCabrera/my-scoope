import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("entity card headings expose an accessible detail link without making the whole card interactive", async () => {
  const product = await readTestFile(
    path.resolve(process.cwd(), "src/components/ui/product.tsx"),
    "utf8",
  );
  const nutritionCard = await readTestFile(
    path.resolve(process.cwd(), "src/components/nutrition/nutrition-entity-card.tsx"),
    "utf8",
  );

  assertSourceMatch(product, /export type EntityHeadingLink = \{[\s\S]*label: string;[\s\S]*onPress\(\): void;/);
  assertSourceMatch(product, /accessibilityLabel=\{headingLink\.label\}[\s\S]*accessibilityRole="link"[\s\S]*onPress=\{headingLink\.onPress\}/);
  assertSourceMatch(product, /<EntityHeading[\s\S]*headingLink=\{headingLink\}/);
  assertSourceMatch(product, /function isGramQuantity[\s\S]*\^\[\\d\.,\]\+\\s\*g\$/);
  assertSourceMatch(product, /function FoodGramChip[\s\S]*backgroundColor=\{`\$\{tokens\.color\.food\}1A`\}[\s\S]*borderColor=\{tokens\.color\.food\}[\s\S]*textColor=\{tokens\.color\.entityIconForeground\}/);
  assertSourceMatch(product, /entity === "food" && isGramQuantity\(indicator\.value\)[\s\S]*<FoodGramChip key=\{key\} value=\{indicator\.value\}/);
  assertSourceMatch(product, /subtitle \? entity === "food" && isGramQuantity\(subtitle\) \? <FoodGramChip value=\{subtitle\} \/>/);
  assertSourceMatch(nutritionCard, /headingLink\?: EntityHeadingLink/);
  assertSourceMatch(nutritionCard, /headingLink=\{headingLink\}/);
});

test("cards with entity-detail actions also link their heading section", async () => {
  const files = await Promise.all([
    "src/components/libraries/library-card.tsx",
    "src/components/libraries/entity-panels.tsx",
    "src/components/libraries/program-daily-plan-preview.tsx",
    "src/components/calendarization/pinned-daily-plan-card.tsx",
    "src/components/calendarization/calendarized-daily-plan-card.tsx",
    "src/components/details/food-detail-card-list.tsx",
    "src/components/proposals/proposal-preview.tsx",
    "src/components/proposals/proposal-program-preview.tsx",
    "src/app/program/days/[id].tsx",
    "src/app/share/[id].tsx",
  ].map((file) => readTestFile(path.resolve(process.cwd(), file), "utf8")));

  for (const source of files) {
    assertSourceMatch(source, /headingLink=/);
  }

  const comparisonList = await readTestFile(
    path.resolve(process.cwd(), "src/app/comparator/index.tsx"),
    "utf8",
  );
  assertSourceMatch(comparisonList, /accessibilityLabel=\{`Ver detalle de \$\{item\.name\}`\}[\s\S]*accessibilityRole="link"[\s\S]*style=\{\(\{ pressed \}\) => \[styles\.savedCopy/);
  assert.equal(files.length, 10);
});
