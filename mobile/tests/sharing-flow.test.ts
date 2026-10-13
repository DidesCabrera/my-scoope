import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("every library entity opens native sharing directly with one portable resource", async () => {
  const actions = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-actions.tsx"), "utf8");
  const adapter = await readTestFile(path.resolve(process.cwd(), "src/sharing/native-share.ts"), "utf8");
  const packageJson = JSON.parse(await readTestFile(path.resolve(process.cwd(), "package.json"), "utf8"));

  assertSourceMatch(packageJson.dependencies["expo-clipboard"], /^~57\./);
  assertSourceMatch(actions, /\/api\/v1\/shares\/\$\{entitySlug\}\/\$\{item\.id\}/);
  assertSourceMatch(actions, /entitySlug: "foods" \| "meals" \| "daily-plans" \| "programs"/);
  assertSourceMatch(actions, /action\.key === "share"[\s\S]*?void shareItem\(\)/);
  assertSourceMatch(actions, /setDismissShareImmediately\(true\);[\s\S]*?setVisible\(false\);[\s\S]*?requestAnimationFrame\(\(\) => requestAnimationFrame[\s\S]*?await openNativeShare\(resource\)/);
  assertSourceDoesNotMatch(actions, /submitting && !selected/);
  assertSourceMatch(actions, /openNativeShare\(resource\)/);
  assertSourceDoesNotMatch(actions, /Compartir con otra app|Copiar enlace|Correo del destinatario/);
  assertSourceMatch(adapter, /Share\.share/);
  assertSourceMatch(adapter, /Clipboard\.setStringAsync/);
});

test("brief native share transitions do not reschedule the full reminder queue", async () => {
  const rootLayout = await readTestFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");

  assertSourceMatch(rootLayout, /inactiveSince\.current \?\?= Date\.now\(\)/);
  assertSourceMatch(rootLayout, /inactiveDuration != null && inactiveDuration >= 10_000/);
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
  assertSourceMatch(shareScreen, /eyebrow="Plan diario"/);
  assertSourceDoesNotMatch(shareScreen, /eyebrow="Plan diario compartido"/);
  assertSourceMatch(shareScreen, /<MealPanels items=\{mealItems\}/);
  assertSourceMatch(shareScreen, /title="Composición plan diario"[\s\S]*Detalle de cada Comida/);
  assertSourceMatch(shareScreen, /<NutritionEntityCard/);
  assertSourceMatch(shareScreen, /<FoodPanels[\s\S]*?items=\{sharedFoodPanelItems\(meal\)\}/);
  assertSourceMatch(shareScreen, /onOpenItem=\{\(food\) => \{ if \(food\.detailId != null\) router\.push\(`\/share\/\$\{id\}\/meals\/\$\{index\}\/foods\/\$\{food\.detailId\}` as Href\); \}\}/);
  assertSourceMatch(shareScreen, /sharedPlanFoodPanelItems\(meals, snapshot\.nutrition\.calories\)/);
  assertSourceMatch(shareScreen, /title="Alimentos en este plan diario"[\s\S]*<GroupedFoodsCard items=\{planFoodItems\} title="Alimentos plan diario" \/>/);
  assertSourceMatch(shareScreen, /planFoodItems\.length/);
});

test("standalone shared foods and meals render complete native detail views", async () => {
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const sharedMealFood = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/foods/[foodIndex].tsx"), "utf8");
  const sharingTypes = await readTestFile(path.resolve(process.cwd(), "src/sharing/types.ts"), "utf8");

  assertSourceMatch(shareScreen, /resource\?\.subject_type === "food"[\s\S]*entity="food"[\s\S]*nutrition=\{sharedNutrition\(snapshot\.nutrition\)\}/);
  assertSourceMatch(shareScreen, /<NutritionFactsCard[\s\S]*facts=\{sharedNutritionFacts\(snapshot\.nutrition\)\}[\s\S]*portion=\{\{ quantity: null, unit: snapshot\.summary\.basis_unit \?\? "g" \}\}/);
  assertSourceMatch(shareScreen, /resource\?\.subject_type === "meal"[\s\S]*entity="meal"[\s\S]*items=\{sharedMealFoods\}/);
  assertSourceMatch(shareScreen, /`\/share\/\$\{id\}\/foods\/\$\{food\.detailId\}`/);
  assertSourceMatch(sharedMealFood, /resource\?\.subject_type === "meal" \? resource\.snapshot\?\.foods\?\.\[position\]/);
  assertSourceMatch(sharedMealFood, /entity="food"/);
  assertSourceMatch(sharedMealFood, /<NutritionFactsCard[\s\S]*facts=\{sharedNutritionFacts\(food\.nutrition\)\}/);
  assertSourceMatch(sharingTypes, /time\?: string \| null/);
});

test("shared programs and comparisons have complete native detail views", async () => {
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const presentation = await readTestFile(path.resolve(process.cwd(), "src/sharing/presentation.ts"), "utf8");
  const comparisonActions = await readTestFile(path.resolve(process.cwd(), "src/app/comparator/saved/[id].tsx"), "utf8");
  const comparisonActionsModal = await readTestFile(path.resolve(process.cwd(), "src/components/comparisons/saved-comparison-actions.tsx"), "utf8");

  assertSourceMatch(shareScreen, /sharedProgramLibraryItem\(snapshot, resource\.title\)/);
  assertSourceMatch(shareScreen, /<Screen[\s\S]*scroll=\{!sharedProgram\}/);
  assertSourceMatch(shareScreen, /<ProgramDetailPreview footer=\{libraryAction\} item=\{sharedProgram\} scrollable showWeekAnalytics=\{false\} \/>/);
  assertSourceMatch(shareScreen, /!sharedProgram \? libraryAction : null/);
  assertSourceMatch(shareScreen, /sharedComparisonResult\(snapshot\)/);
  assertSourceMatch(shareScreen, /<AppHeader eyebrow=\{`Comparación \$\{sharedComparison\.kind_label\}`\} eyebrowIcon=\{<EntityIcon entity=\{comparisonEntity\}/);
  assertSourceMatch(shareScreen, /label=\{`\$\{sharedComparison\.items\.length\} \$\{comparisonCountLabel\}`\}/);
  assertSourceMatch(shareScreen, /<ComparisonItemsSummary items=\{sharedComparison\.items\} \/>/);
  assertSourceMatch(shareScreen, /accessibilityLabel="Vista de la comparación compartida"/);
  assertSourceMatch(shareScreen, /key: "cards", label: "Cards"[\s\S]*key: "table", label: "Tabla"[\s\S]*key: "entities", label: sharedComparison\.kind_label/);
  assertSourceMatch(shareScreen, /comparisonTab === "cards" \? <ComparisonResultCards hideHeader interactive=\{false\} result=\{sharedComparison\} \/>/);
  assertSourceMatch(shareScreen, /comparisonTab === "table" \? <SavedComparisonPreviewPanels items=\{sharedComparison\.items\} scope=\{comparisonEntity\} \/>/);
  assertSourceMatch(shareScreen, /comparisonTab === "entities" \? sharedComparison\.items\.map[\s\S]*?<NutritionEntityCard/);
  assertSourceMatch(shareScreen, /saved\.entity === "comparison" \? `\/comparator\/saved\/\$\{saved\.item_id\}`/);
  assertSourceMatch(presentation, /export function sharedProgramLibraryItem/);
  assertSourceMatch(presentation, /function aggregateSharedFoods/);
  assertSourceMatch(presentation, /const key = `\$\{food\.name\.trim\(\)\.toLocaleLowerCase\("es-CL"\)\}:\$\{unit\}`/);
  assertSourceMatch(presentation, /current\.quantity_grams \+= food\.quantity_grams/);
  assertSourceMatch(presentation, /current\.nutrition = sumNutrition\(\[current\.nutrition, food\.nutrition\]\)/);
  assertSourceMatch(presentation, /aggregateSharedFoods\(sourceDays\.flatMap/);
  assertSourceMatch(presentation, /export function sharedComparisonResult/);
  assertSourceMatch(comparisonActions, /`\/api\/v1\/shares\/comparisons\/\$\{comparison\.saved_comparison_id\}`/);
  assertSourceMatch(comparisonActionsModal, /const resource = await onShare\(\);[\s\S]*?setDismissShareImmediately\(true\);[\s\S]*?onClose\(\);[\s\S]*?requestAnimationFrame\(\(\) => requestAnimationFrame[\s\S]*?await openNativeShare\(resource\)/);
  assertSourceMatch(comparisonActionsModal, /<ActionSheetModal dismissImmediately=\{dismissShareImmediately\}/);
  assertSourceMatch(comparisonActionsModal, /<ActionSheetActions>[\s\S]*label="Compartir"[\s\S]*label=\{compact \? "Renombrar" : "Editar nombre"\}[\s\S]*label="Editar comparación"[\s\S]*label="Eliminar"/);
  assertSourceMatch(comparisonActionsModal, /label=\{compact \? "Renombrar" : "Editar nombre"\}[\s\S]*label="Editar comparación"/);
  assertSourceMatch(comparisonActionsModal, /label="Eliminar comparación"[\s\S]*variant="danger"/);
  assertSourceMatch(comparisonActions, /onShare=\{async \(\) => \{[\s\S]*?return apiRequest<ShareResource>/);
});

test("shared meal foods navigate from panels and detail cards", async () => {
  const sharedMeal = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id]/meals/[mealIndex].tsx"), "utf8");
  const presentation = await readTestFile(path.resolve(process.cwd(), "src/sharing/presentation.ts"), "utf8");
  const foodCards = await readTestFile(path.resolve(process.cwd(), "src/components/details/food-detail-card-list.tsx"), "utf8");

  assertSourceMatch(presentation, /detailId: index/);
  assertSourceMatch(sharedMeal, /<FoodPanels items=\{foods\} onOpenItem=\{openFood\} \/>/);
  assertSourceMatch(sharedMeal, /title="Composición comida"/);
  assertSourceMatch(sharedMeal, /<FoodDetailCardList[\s\S]*onOpenFood=\{openFood\}/);
  assertSourceMatch(sharedMeal, /eyebrowAccessory=\{meal\.time \? <HeaderMetadataChip kind="time" value=\{meal\.time\.slice\(0, 5\)\} \/> : undefined\}/);
  assertSourceMatch(sharedMeal, /eyebrow="Comida"/);
  assertSourceDoesNotMatch(sharedMeal, /eyebrow="Comida compartida"/);
  assertSourceDoesNotMatch(sharedMeal, /label: "hora", tone: "surfaceCard"/);
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
  assertSourceDoesNotMatch(sharedFood, /<EntityDetailMetadata/);
  assertSourceMatch(sharedFood, /eyebrow="Alimento"/);
  assertSourceDoesNotMatch(sharedFood, /eyebrow="Alimento compartido"/);
  assertSourceMatch(information, /<EntityDetailMetadata/);
  assertSourceMatch(information, /creator="Elemento compartido"/);
  assertSourceMatch(information, /creatorLabel="Origen"/);
  assertSourceMatch(information, /updatedAt=\{sharedDate\(resource\.created_at\)\}/);
  assertSourceMatch(information, /updatedAtLabel="Compartido"/);
  assertSourceDoesNotMatch(information, /forceFallback/);
  assertSourceMatch(presentation, /export function sharedDate/);
});

test("native Inbox manages messages while shared detail owns saving to the library", async () => {
  const inbox = await readTestFile(path.resolve(process.cwd(), "src/app/inbox.tsx"), "utf8");
  const inboxActions = await readTestFile(path.resolve(process.cwd(), "src/components/sharing/inbox-item-actions.tsx"), "utf8");
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
  assertSourceMatch(inbox, /<Screen[\s\S]*scrollHeader=\{<SectionPageHeader countLabel="elementos" section="inbox" subtitle="Envía y recibe los elementos que desees con otros usuarios para complementar tu librería y conocimiento\." title="Compartidos" \/>\}/);
  assertSourceMatch(inbox, /stickyHeader=\{<DistributedTabBar<SharingScope>/);
  assertSourceMatch(inbox, /stickyHeaderStyle=\{styles\.stickyHeader\}/);
  assertSourceMatch(inbox, /stickyHeader: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding, paddingTop: tokens\.spacing\.sm \}/);
  assertSourceDoesNotMatch(inbox, /<SectionPageHeader[^>]*count=/);
  assertSourceMatch(inbox, /method: "PATCH"/);
  assertSourceMatch(inbox, /\/api\/v1\/shares\/\$\{item\.resource_id\}[\s\S]*method: "DELETE"/);
  assertSourceMatch(inbox, /MoreHorizontal/);
  assertSourceMatch(inbox, /label=\{`Más acciones para \$\{item\.title\}`\}/);
  assertSourceMatch(inbox, /<InboxItemActions/);
  assertSourceMatch(inboxActions, /label="Revocar acceso"/);
  assertSourceMatch(inboxActions, /label="Confirmar revocación"/);
  assertSourceMatch(inboxActions, /setConfirmingRevoke\(true\)/);
  assertSourceMatch(inboxActions, /label="Eliminar de Recibidos"/);
  assertSourceMatch(inbox, /current\.sent\.items\.filter\(\(\{ resource_id \}\) => resource_id !== item\.resource_id\)/);
  assertSourceMatch(inbox, /item\.status === "revoked" \|\| item\.status === "expired"/);
  assertSourceMatch(inbox, /comparison: \{ feminine: true, label: "Comparación" \}/);
  assertSourceMatch(inbox, /daily_plan: \{ feminine: false, label: "Plan diario" \}/);
  assertSourceMatch(inbox, /meal: \{ feminine: true, label: "Comida" \}/);
  assertSourceMatch(inbox, /activeScope === "received"[\s\S]*eyebrow\.feminine \? "Recibida" : "Recibido"[\s\S]*eyebrow\.feminine \? "Enviada" : "Enviado"/);
  assertSourceMatch(inbox, /<ProposalStatusBadge label=\{item\.status === "expired" \? "Enlace vencido" : "Acceso revocado"\} status="rejected" \/>/);
  assertSourceMatch(inbox, /item\.is_read \|\| unavailable[\s\S]*<MailOpen/);
  assertSourceMatch(inbox, /style=\{styles\.unavailableAction\}[\s\S]*<Ban/);
  assertSourceMatch(inbox, /`Recibido de \$\{item\.sender\}`/);
  assertSourceMatch(inbox, /activeScope === "received" \? `Recibido de \$\{item\.sender\}` : "Enviado"/);
  assertSourceMatch(inbox, /onPress=\{unavailable \? undefined/);
  assertSourceMatch(inbox, /<EntityCard/);
  assertSourceMatch(inbox, /<EntityCardAction/);
  assertSourceMatch(inbox, /comparisonLabelByKind[\s\S]*?dailyplans: "Planes diarios"[\s\S]*?foods: "Alimentos"[\s\S]*?meals: "Comidas"/);
  assertSourceMatch(inbox, /eyebrow=\{`\$\{eyebrowLabel\} \$\{directionLabel\}`\}/);
  assertSourceMatch(inbox, /identityColor=\{comparisonAccent\}/);
  assertSourceMatch(inbox, /<CollectionEmptyState/);
  assertSourceMatch(inbox, /<LoadingState label="Cargando compartidos…" mode="content" \/>/);
  assertSourceMatch(shareScreen, /<LoadingState label="Cargando contenido compartido…" mode="content" \/>/);
  assertSourceMatch(inbox, /daily_plan: "dailyPlan"/);
  assertSourceMatch(inbox, /comparison: "comparison"/);
  assertSourceMatch(inbox, /comparisonEntityByKind/);
  assertSourceMatch(inbox, /dailyplans: "dailyPlan"/);
  assertSourceMatch(inbox, /foods: "food"/);
  assertSourceMatch(inbox, /meals: "meal"/);
  assertSourceMatch(inbox, /const comparisonAccent = sharedCardAccent\(item\)[\s\S]*accent=\{comparisonAccent\}/);
  assertSourceMatch(shareScreen, /\/api\/v1\/shares\/inbox\/\$\{inboxItemId\}\/save/);
  assertSourceMatch(shareScreen, /`\/libraries\/\$\{libraryPathByEntity\[saved\.entity\]\}\/\$\{saved\.item_id\}`/);
  assertSourceMatch(navigation, /href: "\/inbox"/);
});

test("owners can preview their shares without claiming them into their own Inbox", async () => {
  const shareScreen = await readTestFile(path.resolve(process.cwd(), "src/app/share/[id].tsx"), "utf8");
  const errors = await readTestFile(path.resolve(process.cwd(), "src/api/errors.ts"), "utf8");

  assertSourceMatch(shareScreen, /apiRequest<SharingInboxData>\("\/api\/v1\/shares\/inbox\?scope=sent"\)/);
  assertSourceMatch(shareScreen, /setIsOwnedResource\(sent\.items\.some\(\(candidate\) => candidate\.resource_id === id\)\)/);
  assertSourceMatch(shareScreen, /isOwnedResource \? \([\s\S]*Este contenido ya pertenece a tu biblioteca\./);
  assertSourceMatch(errors, /share_self_claim_not_allowed: "Este contenido ya pertenece a tu biblioteca\."/);
  assertSourceMatch(errors, /share_self_recipient_not_allowed: "No puedes compartir contenido contigo mismo\."/);
});
