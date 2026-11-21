import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const contractPath = path.join(repositoryRoot, "design/ui-contract.json");
const cssPath = path.join(repositoryRoot, "notas/static/notas/css/ui-contract.generated.css");
const nativePath = path.join(repositoryRoot, "mobile/src/generated/ui-tokens.ts");
const mcpCardSources = ["meal_card_v6", "meal_card_v7", "meal_card_v8", "entity_card_v1", "entity_card_v2"].map((name) => ({
  sourcePath: path.join(repositoryRoot, `mcp_server/myscoope_mcp/ui/${name}.source.html`),
  outputPath: path.join(repositoryRoot, `mcp_server/myscoope_mcp/ui/${name}.html`),
}));
const proposalCardCssPath = path.join(repositoryRoot, "mcp_server/myscoope_mcp/ui/proposal_card_v1.css");
const proposalCardExtensionPath = path.join(repositoryRoot, "mcp_server/myscoope_mcp/ui/proposal_card_v1.extension.html");
const proposalCardOutputPath = path.join(repositoryRoot, "mcp_server/myscoope_mcp/ui/proposal_card_v1.html");
const mcpTokenMarker = "/* MYSCOOPE_GENERATED_UI_TOKENS */";

const contract = JSON.parse(await readFile(contractPath, "utf8"));
const { shared, platforms } = contract;

const kebab = (value) => value.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
const px = (value) => `${value}px`;
const cssLines = (values, prefix, format = (value) => value) =>
  Object.entries(values).map(([key, value]) => `  --${prefix}${kebab(key)}: ${format(value)};`);

const componentRecipeCssLines = (recipes) => Object.entries(recipes).flatMap(
  ([component, variants]) => Object.entries(variants).flatMap(
    ([variant, values]) => cssLines(values, `${kebab(component)}-${kebab(variant)}-`, px),
  ),
);

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
const webDarkEntityLines = Object.entries(platforms.web.themes.dark.entities ?? {}).flatMap(([key, value]) => {
  if (!(key in shared.entities)) throw new Error(`Unknown web dark entity: ${key}`);
  const name = entityVariable[key] ?? kebab(key);
  return [`  --entity-${name}: ${value};`, `  --color-${name}: ${value};`];
});
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
  ...componentRecipeCssLines(platforms.web.componentRecipes),
  ...entityLines,
  ...nutritionLines,
  "}",
  "",
  "html[data-theme=\"dark\"] {",
  ...themeCss(dark),
  ...webDarkEntityLines,
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
  radius: { ...shared.radius, ...platforms.native.overrides.radius },
  type: shared.typography,
  weight: shared.fontWeight,
  card: platforms.native.overrides.card,
  layout: platforms.native.overrides.layout,
  component: platforms.native.componentRecipes,
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

const mcpTheme = platforms[platforms.mcp.themeSource].themes;
const mcpTokens = [
  "/* Generated from design/ui-contract.json. Edit that contract, not this block. */",
  ":root {",
  `  --ui-contract-version: "${contract.contract}";`,
  `  --font-family-sans: ${platforms.web.fontFamily};`,
  ...cssLines(shared.spacing, "space-", (value) => `${value / 16}rem`),
  ...cssLines(shared.radius, "radius-", px),
  ...cssLines(shared.typography, "font-size-", px),
  ...cssLines(shared.fontWeight, "font-weight-"),
  ...componentRecipeCssLines(platforms.mcp.componentRecipes),
  ...entityLines,
  ...nutritionLines,
  ...themeCss(mcpTheme.light),
  "}",
  ':root[data-theme="dark"] {',
  ...themeCss(mcpTheme.dark),
  "}",
  "@media (prefers-color-scheme: dark) {",
  "  :root:not([data-theme]) {",
  ...themeCss(mcpTheme.dark),
  "  }",
  "}",
].join("\n");
const mcpCards = await Promise.all(mcpCardSources.map(async ({sourcePath, outputPath}) => {
  const source = await readFile(sourcePath, "utf8");
  if (source.split(mcpTokenMarker).length !== 2) {
    throw new Error(`Expected exactly one ${mcpTokenMarker} in ${sourcePath}`);
  }
  return {outputPath, content: source.replace(mcpTokenMarker, mcpTokens)};
}));
// Compose the proposal shell around the existing DailyPlan card, retaining its
// renderer, tabs, responsive panels and UI System tokens in one MCP resource.
const dailyPlanCard = mcpCards.find(({outputPath}) => outputPath.endsWith("/entity_card_v2.html"));
const [proposalCss, proposalExtension] = await Promise.all([
  readFile(proposalCardCssPath, "utf8"),
  readFile(proposalCardExtensionPath, "utf8"),
]);
if (!dailyPlanCard || !dailyPlanCard.content.includes("</head>") || !dailyPlanCard.content.includes("</body>")) {
  throw new Error("DailyPlan card cannot be composed into the proposal resource");
}
const proposalCard = {
  outputPath: proposalCardOutputPath,
  content: dailyPlanCard.content
    .replace("</head>", `<style>\n${proposalCss}</style>\n</head>`)
    .replace("</body>", `${proposalExtension}\n</body>`),
};
mcpCards.push(proposalCard);

if (process.argv.includes("--check")) {
  const [currentCss, currentNative, ...currentMcpCards] = await Promise.all([
    readFile(cssPath, "utf8").catch(() => ""),
    readFile(nativePath, "utf8").catch(() => ""),
    ...mcpCards.map(({outputPath}) => readFile(outputPath, "utf8").catch(() => "")),
  ]);
  if (currentCss !== css || currentNative !== native || mcpCards.some(({content}, index) => currentMcpCards[index] !== content)) {
    console.error("Generated UI tokens are stale. Run: npm run generate:ui");
    process.exitCode = 1;
  }
} else {
  await Promise.all([
    mkdir(path.dirname(cssPath), { recursive: true }),
    mkdir(path.dirname(nativePath), { recursive: true }),
  ]);
  await Promise.all([writeFile(cssPath, css), writeFile(nativePath, native), ...mcpCards.map(({outputPath, content}) => writeFile(outputPath, content))]);
  console.log(`Generated UI assets, including ${mcpCards.map(({outputPath}) => path.relative(repositoryRoot, outputPath)).join(", ")}`);
}
