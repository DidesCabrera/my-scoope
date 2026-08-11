import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const contractPath = path.join(repositoryRoot, "design/ui-contract.json");
const cssPath = path.join(repositoryRoot, "notas/static/notas/css/ui-contract.generated.css");
const nativePath = path.join(repositoryRoot, "mobile/src/generated/ui-tokens.ts");

const contract = JSON.parse(await readFile(contractPath, "utf8"));
const { shared, platforms } = contract;

const kebab = (value) => value.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
const px = (value) => `${value}px`;
const cssLines = (values, prefix, format = (value) => value) =>
  Object.entries(values).map(([key, value]) => `  --${prefix}${kebab(key)}: ${format(value)};`);

function themeCss(theme) {
  const direct = {
    surfaceApp: "surface-app",
    surfacePage: "surface-page",
    surfaceCard: "surface-card",
    surfaceMuted: "surface-card-muted",
    surfaceElevated: "surface-elevated",
    textMain: "text-main",
    textMuted: "text-muted",
    textSoft: "text-soft",
    textSubtle: "text-subtle",
    textInverted: "text-inverted",
    textLink: "text-link",
    borderSoft: "border-soft",
    borderDefault: "border-default",
    borderStrong: "border-strong",
    interactivePrimary: "interactive-primary",
    interactivePressed: "interactive-primary-hover",
    danger: "status-danger",
    success: "status-success",
    warning: "status-warning",
    kcalSurface: "nutrition-kcal",
    kcalBorder: "nutrition-kcal-border",
    allocationBarTrack: "alloc-bar-bg",
    allocationPanelTrack: "alloc-cell-bg",
  };
  return Object.entries(direct)
    .filter(([key]) => theme[key] !== undefined)
    .map(([key, variable]) => `  --${variable}: ${theme[key]};`);
}

const webSpacing = {
  1: shared.spacing.xs,
  2: shared.spacing.sm,
  3: shared.spacing.md,
  4: shared.spacing.lg,
  ...platforms.web.overrides.spacing,
};
const entityVariable = {
  dailyPlan: "dailyplan",
};
const entityLines = Object.entries(shared.entities).map(
  ([key, value]) => `  --entity-${entityVariable[key] ?? kebab(key)}: ${value};`,
);
const nutritionVariable = {
  quantity: "qty",
};
const nutritionLines = Object.entries(shared.nutrition).map(
  ([key, value]) => `  --nutrition-${nutritionVariable[key] ?? kebab(key)}: ${value};`,
);

const light = platforms.web.themes.light;
const dark = platforms.web.themes.dark;
const css = [
  "/* This file is generated from design/ui-contract.json. Do not edit by hand. */",
  ":root {",
  `  --ui-contract-version: "${contract.contract}";`,
  `  --font-family-sans: ${platforms.web.fontFamily};`,
  ...themeCss(light),
  ...cssLines(shared.spacing, "space-", (value) => `${value / 16}rem`),
  ...cssLines(webSpacing, "space-", (value) => `${value / 16}rem`),
  ...cssLines(shared.radius, "radius-", px),
  `  --radius-xl: ${px(shared.radius.card)};`,
  ...cssLines(shared.typography, "font-size-", px),
  ...cssLines(shared.fontWeight, "font-weight-"),
  ...entityLines,
  ...nutritionLines,
  "}",
  "",
  "html[data-theme=\"dark\"] {",
  ...themeCss(dark),
  "}",
  "",
].join("\n");

const nativeEntities = { ...shared.entities, ...platforms.native.overrides.entities };
const nativeTokens = {
  contract: contract.contract,
  mode: platforms.native.mode,
  color: {
    ...platforms.native.theme,
    ...shared.nutrition,
    protein: shared.nutrition.protein,
    carbs: shared.nutrition.carbs,
    fat: shared.nutrition.fat,
    ...nativeEntities,
  },
  spacing: { ...shared.spacing, ...platforms.native.overrides.spacing },
  radius: shared.radius,
  type: shared.typography,
  weight: shared.fontWeight,
  card: platforms.native.overrides.card,
  layout: platforms.native.overrides.layout,
};

const native = [
  "// This file is generated from design/ui-contract.json. Do not edit by hand.",
  `export const tokens = ${JSON.stringify(nativeTokens, null, 2)} as const;`,
  "",
  `export const font = ${JSON.stringify(platforms.native.fontFamily, null, 2)} as const;`,
  "",
  "export type VisualTokens = typeof tokens;",
  "",
].join("\n");

if (process.argv.includes("--check")) {
  const [currentCss, currentNative] = await Promise.all([
    readFile(cssPath, "utf8").catch(() => ""),
    readFile(nativePath, "utf8").catch(() => ""),
  ]);
  if (currentCss !== css || currentNative !== native) {
    console.error("Generated UI tokens are stale. Run: npm run generate:ui");
    process.exitCode = 1;
  }
} else {
  await Promise.all([
    mkdir(path.dirname(cssPath), { recursive: true }),
    mkdir(path.dirname(nativePath), { recursive: true }),
  ]);
  await Promise.all([writeFile(cssPath, css), writeFile(nativePath, native)]);
  console.log(`Generated ${path.relative(repositoryRoot, cssPath)} and ${path.relative(repositoryRoot, nativePath)}`);
}
