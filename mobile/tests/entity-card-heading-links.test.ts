import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

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
  assertSourceMatch(product, /accessibilityLabel=\{headingLink\.label\}[\s\S]*accessibilityRole="link"[\s\S]*onPress=\{\(\) => runGuardedNavigation\(headingLink\.onPress\)\}/);
  assertSourceMatch(product, /<EntityHeading[\s\S]*headingLink=\{headingLink\}/);
  assertSourceMatch(product, /function isFoodQuantity[\s\S]*g\|ml/);
  assertSourceMatch(product, /import \{ foodNutritionBasisLabel \} from "\.\/food-nutrition-basis"/);
  assertSourceMatch(product, /function NutritionBasisSubtitle[\s\S]*foodNutritionBasisLabel\(value\)[\s\S]*value\.startsWith\("Rinde "\)[\s\S]*Información nutricional:/);
  assertSourceMatch(product, /return <Text style=\{styles\.headingSubtitle\}>\{label\}<\/Text>/);
  assertSourceMatch(product, /entity === "food" && isFoodQuantity\(indicator\.value\)[\s\S]*<NutritionBasisSubtitle entity="food" key=\{key\} value=\{indicator\.value\}/);
  assertSourceMatch(product, /subtitle \? entity === "preparation" \|\| entity === "food" && isFoodQuantity\(subtitle\) \? <NutritionBasisSubtitle/);
  assertSourceMatch(nutritionCard, /headingLink\?: EntityHeadingLink/);
  assertSourceMatch(nutritionCard, /headingLink=\{headingLink\}/);
});

test("preparation cards show selected portions while the detail states recipe yield", async () => {
  const picker = await readTestFile(path.resolve(process.cwd(), "src/components/preparations/preparation-picker-card.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/app/libraries/preparations/[id].tsx"), "utf8");
  const componentCards = await readTestFile(path.resolve(process.cwd(), "src/components/details/food-detail-card-list.tsx"), "utf8");

  assertSourceMatch(picker, /subtitle=\{preparationPortionLabel\(detail\)\}/);
  assertSourceDoesNotMatch(picker, /indicators=\{\[\{ label: "porción"/);
  assertSourceMatch(detail, /<EntityDetailPage entity="preparation"[^>]*subtitle=\{subtitle\}/);
  assertSourceMatch(detail, /Rinde \$\{formatPreparationNumber\(detail\.yield_g, 2\)\} g/);
  assertSourceMatch(detail, /\/api\/v1\/preparations\/\$\{id\}\?full_recipe=true/);
  assertSourceMatch(componentCards, /entity=\{isPreparation \? "preparation" : "food"\}[\s\S]*subtitle=\{`\$\{item\.quantity\} \$\{item\.quantityUnit\}`\}/);
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
    path.resolve(process.cwd(), "src/components/comparisons/saved-comparison-list-card.tsx"),
    "utf8",
  );
  assertSourceMatch(comparisonList, /accessibilityLabel=\{`Ver detalle de \$\{item\.name\}`\}[\s\S]*accessibilityRole="link"[\s\S]*style=\{\(\{ pressed \}\) => \[styles\.savedCopy/);
  assert.equal(files.length, 10);
});
