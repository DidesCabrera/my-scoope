import { access, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];

async function source(relativePath) {
  return readFile(path.join(repositoryRoot, relativePath), "utf8");
}

async function requireMatch(relativePath, pattern, message) {
  const value = await source(relativePath);
  if (!pattern.test(value)) failures.push(`${relativePath}: ${message}`);
}

async function requireAbsent(relativePath, message) {
  try {
    await access(path.join(repositoryRoot, relativePath));
    failures.push(`${relativePath}: ${message}`);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}

await Promise.all([
  requireAbsent(
    "mobile/src/components/libraries/entity-card.tsx",
    "the library must use the canonical public EntityCard",
  ),
  requireAbsent(
    "mobile/src/components/libraries/entity-detail-page.tsx",
    "the library must use the canonical detail-page composition",
  ),
  requireAbsent(
    "mobile/src/components/libraries/nutrition-entity-card.tsx",
    "the library must use the canonical public NutritionEntityCard",
  ),
  requireMatch(
    "mobile/src/components/nutrition/nutrition-kpi-section.tsx",
    /tokens\.component\.nutritionKpi\.regular\.totalSize/,
    "NutritionKpiSection must consume the generated component recipe",
  ),
  requireMatch(
    "mobile/src/components/nutrition/nutrition-kpi-section.tsx",
    /variant\?: "nested" \| "regular"/,
    "KPI variants must be semantic rather than raw density choices",
  ),
  requireMatch(
    "notas/static/notas/css/components/dash_kpi.css",
    /var\(--nutrition-kpi-regular-total-size\)/,
    "web Dash KPI must consume the generated component recipe",
  ),
  requireMatch(
    "notas/templates/notas/dev/ui_system_gallery.html",
    /include "components\/dash_kpi\.html"/,
    "the Web gallery must render the production Dash KPI partial",
  ),
  requireMatch(
    "notas/templates/notas/dev/ui_system_gallery.html",
    /include "components\/card_child_program\.html"/,
    "the Web gallery must render the production Program card partial",
  ),
  requireMatch(
    "mobile/src/app/dev/ui-gallery.tsx",
    /from "@\/components\/nutrition"/,
    "the Native gallery must import the public nutrition components",
  ),
]);

if (failures.length) {
  console.error("UI architecture contract failed:\n");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exitCode = 1;
} else {
  console.log("UI architecture contract is valid.");
}
