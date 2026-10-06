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
  assertSourceMatch(actions, /setDismissShareImmediately\(true\);[\s\S]*?setVisible\(false\);[\s\S]*?requestAnimationFrame\(\(\) => requestAnimationFrame[\s\S]*?await openNativeShare\(resource\)/);
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
  assertSourceMatch(shareScreen, /<FoodPanels[\s\S]*?items=\{sharedFoodPanelItems\(meal\)\}/);
  assertSourceMatch(shareScreen, /onOpenItem=\{\(food\) => \{ if \(food\.detailId != null\) router\.push\(`\/share\/\$\{id\}\/meals\/\$\{index\}\/foods\/\$\{food\.detailId\}` as Href\); \}\}/);
});

test("shared meal foods navigate from panels and detail cards", async () => {
  const sharedMeal = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/meals/[mealIndex].tsx"), "utf8");
  const presentation = await readTestFile(path.resolve(process.cwd(), "src/sharing/presentation.ts"), "utf8");
  const foodCards = await readTestFile(path.resolve(process.cwd(), "src/components/details/food-detail-card-list.tsx"), "utf8");

  assertSourceMatch(presentation, /detailId: index/);
  assertSourceMatch(sharedMeal, /<FoodPanels items=\{foods\} onOpenItem=\{openFood\} \/>/);
  assertSourceMatch(sharedMeal, /<FoodDetailCardList[\s\S]*onOpenFood=\{openFood\}/);
  assertSourceMatch(sharedMeal, /eyebrowAccessory=\{meal\.time \? <HeaderMetadataChip kind="time" value=\{meal\.time\.slice\(0, 5\)\} \/> : undefined\}/);
  assert.doesNotMatch(sharedMeal, /label: "hora", tone: "surfaceCard"/);
  assertSourceMatch(sharedMeal, /`\/share\/\$\{id\}\/meals\/\$\{index\}\/foods\/\$\{food\.detailId\}`/);
  assertSourceMatch(foodCards, /onOpenFood && item\.detailId != null[\s\S]*<ChevronRight/);
});

test("shared details move available item information into the header action", async () => {
  const sharedDetail = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const sharedMeal = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/meals/[mealIndex].tsx"), "utf8");
  const sharedFood = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/meals/[mealIndex]/foods/[foodIndex].tsx"), "utf8");
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/sharing/shared-resource-actions.tsx"), "utf8");
  const information = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/information.tsx"), "utf8");
  const presentation = await readTestFile(path.resolve(process.cwd(), "src/sharing/presentation.ts"), "utf8");

  for (const detail of [sharedDetail, sharedMeal, sharedFood]) {
    assertSourceMatch(detail, /<SharedResourceActions/);
    assertSourceMatch(detail, /`\/share\/\$\{id\}\/information`/);
  }
  assertSourceMatch(actions, /Ver información del elemento/);
  assert.doesNotMatch(sharedFood, /<EntityDetailMetadata/);
  assertSourceMatch(information, /<EntityDetailMetadata/);
  assertSourceMatch(information, /creator="Elemento compartido"/);
  assertSourceMatch(information, /creatorLabel="Origen"/);
  assertSourceMatch(information, /updatedAt=\{sharedDate\(resource\.created_at\)\}/);
  assertSourceMatch(information, /updatedAtLabel="Compartido"/);
  assert.doesNotMatch(information, /forceFallback/);
  assertSourceMatch(presentation, /export function sharedDate/);
});

test("native Inbox manages messages while shared detail owns saving to the library", async () => {
  const inbox = await readTestFile(path.resolve(process.cwd(), "src/app/inbox.tsx"), "utf8");
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const navigation = await readTestFile(path.resolve(process.cwd(), "src/navigation/product-areas.ts"), "utf8");

  assertSourceMatch(inbox, /\/api\/v1\/shares\/inbox/);
  assertSourceMatch(inbox, /\/api\/v1\/shares\/inbox\?scope=sent/);
  assertSourceMatch(inbox, /<DistributedTabBar<SharingScope>/);
  assertSourceMatch(inbox, /label: "Recibidos"/);
  assertSourceMatch(inbox, /label: "Enviados"/);
  assertSourceMatch(inbox, /icon: \(selected\) => <MailOpen color=\{selected \? tokens\.color\.surfaceApp : tokens\.color\.textMuted\}/);
  assertSourceMatch(inbox, /icon: \(selected\) => <Send color=\{selected \? tokens\.color\.surfaceApp : tokens\.color\.textMuted\}/);
  assertSourceMatch(inbox, /count: data\?\.received\.count \?\? 0/);
  assertSourceMatch(inbox, /count: data\?\.sent\.count \?\? 0/);
  assertSourceMatch(inbox, /<Screen[\s\S]*scrollHeader=\{<SectionPageHeader countLabel="elementos" section="inbox" title="Compartidos" \/>\}/);
  assertSourceMatch(inbox, /stickyHeader=\{<DistributedTabBar<SharingScope>/);
  assertSourceMatch(inbox, /stickyHeaderStyle=\{styles\.stickyHeader\}/);
  assertSourceMatch(inbox, /stickyHeader: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding, paddingTop: tokens\.spacing\.sm \}/);
  assert.doesNotMatch(inbox, /<SectionPageHeader[^>]*count=/);
  assertSourceMatch(inbox, /method: "PATCH"/);
  assertSourceMatch(inbox, /<EntityCard/);
  assertSourceMatch(inbox, /<EntityCardAction/);
  assertSourceMatch(inbox, /<CollectionEmptyState/);
  assertSourceMatch(inbox, /daily_plan: "dailyPlan"/);
  assertSourceMatch(shareScreen, /\/api\/v1\/shares\/inbox\/\$\{inboxItemId\}\/save/);
  assertSourceMatch(shareScreen, /`\/libraries\/\$\{libraryPathByEntity\[saved\.entity\]\}\/\$\{saved\.item_id\}`/);
  assertSourceMatch(navigation, /href: "\/inbox"/);
});
