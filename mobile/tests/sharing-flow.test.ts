import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("every library entity opens native sharing directly with one portable resource", async () => {
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-actions.tsx"), "utf8");
  const adapter = await readTestFile(path.resolve(process.cwd(), "src/sharing/native-share.ts"), "utf8");
  const packageJson = JSON.parse(await readTestFile(path.resolve(process.cwd(), "package.json"), "utf8"));

  assert.match(packageJson.dependencies["expo-clipboard"], /^~57\./);
  assertSourceMatch(actions, /\/api\/v1\/shares\/\$\{entitySlug\}\/\$\{item\.id\}/);
  assertSourceMatch(actions, /entitySlug: "foods" \| "meals" \| "daily-plans" \| "programs"/);
  assertSourceMatch(actions, /action\.key === "share"[\s\S]*?void shareItem\(\)/);
  assertSourceMatch(actions, /setVisible\(false\);[\s\S]*?setTimeout\(resolve, 5\)[\s\S]*?await openNativeShare\(resource\)/);
  assert.doesNotMatch(actions, /submitting && !selected/);
  assertSourceMatch(actions, /openNativeShare\(resource\)/);
  assert.doesNotMatch(actions, /Compartir con otra app|Copiar enlace|Correo del destinatario/);
  assertSourceMatch(adapter, /Share\.share/);
  assertSourceMatch(adapter, /Clipboard\.setStringAsync/);
});

test("share deep links preserve their destination through authentication prerequisites", async () => {
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const universalRoute = await readTestFile(path.resolve(process.cwd(), "src/app/s/[id].tsx"), "utf8");
  const rootLayout = await readTestFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");
  const login = await readTestFile(path.resolve(process.cwd(), "src/app/login.tsx"), "utf8");
  const onboarding = await readTestFile(path.resolve(process.cwd(), "src/app/onboarding.tsx"), "utf8");
  const disclosures = await readTestFile(path.resolve(process.cwd(), "src/app/disclosures.tsx"), "utf8");
  const webPreview = await readTestFile(path.resolve(process.cwd(), "../notas/templates/notas/sharing/preview.html"), "utf8");

  assertSourceMatch(shareScreen, /params: \{ returnTo: `\/share\/\$\{id\}` \}/);
  assertSourceMatch(shareScreen, /\/api\/v1\/shares\/\$\{id\}\/claims/);
  assertSourceMatch(universalRoute, /share\/\[id\]/);
  assertSourceMatch(rootLayout, /pathname\.startsWith\("\/s\/"\)/);
  for (const source of [login, onboarding, disclosures]) {
    assertSourceMatch(source, /internalHref\(returnTo\)/);
  }
  assertSourceMatch(webPreview, /myscoope:\/\/share\/\{\{ resource\.public_id \}\}/);
});

test("shared daily plans reuse the native entity detail and nutrition panel system", async () => {
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");

  assertSourceMatch(shareScreen, /<EntityDetailPage/);
  assertSourceMatch(shareScreen, /entity="dailyPlan"/);
  assertSourceMatch(shareScreen, /<MealPanels items=\{mealItems\}/);
  assertSourceMatch(shareScreen, /Detalle de cada Comida/);
  assertSourceMatch(shareScreen, /<NutritionEntityCard/);
  assertSourceMatch(shareScreen, /<FoodPanels items=\{sharedFoodPanelItems\(meal\)\}/);
});

test("native Inbox manages messages while shared detail owns saving to the library", async () => {
  const inbox = await readTestFile(path.resolve(process.cwd(), "src/app/inbox.tsx"), "utf8");
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const navigation = await readTestFile(path.resolve(process.cwd(), "src/navigation/product-areas.ts"), "utf8");

  assertSourceMatch(inbox, /\/api\/v1\/shares\/inbox/);
  assertSourceMatch(inbox, /method: "PATCH"/);
  assertSourceMatch(inbox, /<EntityCard/);
  assertSourceMatch(inbox, /<EntityCardAction/);
  assertSourceMatch(inbox, /<CollectionEmptyState/);
  assertSourceMatch(inbox, /daily_plan: "dailyPlan"/);
  assertSourceMatch(shareScreen, /\/api\/v1\/shares\/inbox\/\$\{inboxItemId\}\/save/);
  assertSourceMatch(shareScreen, /`\/libraries\/\$\{libraryPathByEntity\[saved\.entity\]\}\/\$\{saved\.item_id\}`/);
  assertSourceMatch(navigation, /href: "\/inbox"/);
});
