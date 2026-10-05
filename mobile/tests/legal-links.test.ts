import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("account and disclosures expose the public legal policies", async () => {
  const account = await readTestFile(path.resolve(process.cwd(), "src/app/account.tsx"), "utf8");
  const disclosures = await readTestFile(path.resolve(process.cwd(), "src/app/disclosures.tsx"), "utf8");

  for (const source of [account, disclosures]) {
    assertSourceMatch(source, /\/privacy\//);
    assertSourceMatch(source, /\/terms\//);
    assertSourceMatch(source, /\/refund-policy\//);
  }
  assertSourceMatch(account, /\/support\//);
});

test("subscription screen recognizes every planned billing provider", async () => {
  const subscription = await readTestFile(path.resolve(process.cwd(), "src/app/subscription.tsx"), "utf8");
  const details = await readTestFile(path.resolve(process.cwd(), "src/app/subscription-details.tsx"), "utf8");
  const planCard = await readTestFile(path.resolve(process.cwd(), "src/components/subscriptions/subscription-plan-card.tsx"), "utf8");

  assertSourceMatch(details, /apple_app_store: "App Store"/);
  assertSourceMatch(subscription, /label: "Acciones de suscripciones y bolsas"/);
  assertSourceMatch(subscription, /fallback: "\/account", identityVisible: compactHeaderVisible, mode: "back", title: "Suscripciones y Bolsas"/);
  assertSourceMatch(subscription, /<Screen headerMode="preserve" onHeaderVisibilityChange=\{setCompactHeaderVisible\}>/);
  assertSourceMatch(subscription, /<AppHeader eyebrow="Cuenta" title="Suscripciones y Bolsas" \/>/);
  assertSourceMatch(subscription, /Ver detalles de Suscripciones y Bolsas/);
  assertSourceMatch(subscription, /router\.push\("\/subscription-details" as Href\)/);
  assertSourceMatch(subscription, /<RefreshCcw[^>]*>[\s\S]*Restaurar compras/);
  assertSourceMatch(subscription, /onPress=\{\(\) => \{ closeActions\(\); void restore\(\); \}\}/);
  assertSourceDoesNotMatch(subscription, /<Button\s+label="Restaurar compras"/);
  assertSourceDoesNotMatch(subscription, /Mi suscripción|Planes y Bolsas|Volver a hoy|router\.back\(\)/);
  assertSourceMatch(subscription, /apiRequest<EntitlementsData>\("\/api\/v1\/entitlements"\)/);
  assertSourceMatch(subscription, /<Text style=\{styles\.eyebrow\}>SUSCRIPCIÓN ACTUAL<\/Text>/);
  assertSourceMatch(subscription, /<AssistantCreditBalance availability=\{entitlements\} contained \/>/);
  assertSourceDoesNotMatch(subscription, /<Pill|Estado actual:/);
  assertSourceMatch(details, /google_play: "Google Play"/);
  assertSourceMatch(details, /paddle: "Paddle"/);
  assertSourceDoesNotMatch(details, /mercado_pago: "Mercado Pago"/);
  assertSourceMatch(subscription, /<SectionTitle title="Suscripciones disponibles" titleStyle=\{styles\.commercialSectionTitle\} \/>/);
  assertSourceDoesNotMatch(subscription, /Precio oficial de/);
  assertSourceMatch(subscription, /<SectionDivider \/>\s*<SectionHeading[\s\S]*icon=\{<Sparkles color=\{tokens\.color\.entityIconForeground\} size=\{18\} \/>\}[\s\S]*title="Bolsas de créditos"[\s\S]*titleStyle=\{styles\.commercialSectionTitle\}/);
  assertSourceDoesNotMatch(subscription, /detail=\{Platform\.OS === "android" \? "Google Play" : "App Store"\}/);
  assertSourceDoesNotMatch(subscription, /title="Tu canal de compra"|title="Canales de cobro registrados"/);
  assertSourceMatch(details, /title="Tu canal de compra"/);
  assertSourceMatch(details, /title="Canales de cobro registrados"/);
  assertSourceMatch(details, /fallback: "\/subscription", mode: "back"/);
  assertSourceDoesNotMatch(subscription, /detail="Precio oficial de App Store"/);
  assertSourceMatch(subscription, /productStatusAndroid === "not-found"/);
  assertSourceMatch(subscription, /androidUnavailable \? "No disponible" : "Consultando…"/);
  assertSourceMatch(subscription, /const subscriptionPlans = \["Basic", "Pro"\]\.map/);
  assertSourceMatch(subscription, /<SubscriptionPlanCard accent=\{tokens\.color\.fat\} benefits=\{commercialPlanBenefits\.Free\} caption="Incluido sin costo\." name="Free" price="\$0\/mes" \/>/);
  assertSourceMatch(subscription, /<Card accent=\{subscriptionPlanAccent\(entitlements\?\.plan_name \?\? overview\?\.plan_name\)\}>/);
  assertSourceMatch(subscription, /<SubscriptionPlanCard accent=\{subscriptionPlanAccent\(plan\.planName\) \?\? tokens\.color\.contextual\}[^>]*key=\{plan\.planName\}/);
  assertSourceMatch(subscription, /<Card accent=\{tokens\.color\.carbs\} key=\{configured\.product_id\}>/);
  assertSourceDoesNotMatch(subscription, /<Card key=\{(?:plan\.planName|configured\.product_id)\} muted>/);
  assertSourceMatch(subscription, /item\.plan_name\.trim\(\)\.toLowerCase\(\) === planName\.toLowerCase\(\)/);
  assertSourceMatch(subscription, /name=\{plan\.planName\} price=\{monthlyDisplayPrice \? `\$\{monthlyDisplayPrice\}\/mes` : "Consultando…"\}/);
  assertSourceMatch(planCard, /<Text style=\{styles\.eyebrow\}>PLAN DE SUSCRIPCIÓN<\/Text>[\s\S]*<Text style=\{styles\.productName\}>\{name\}<\/Text>[\s\S]*<Text numberOfLines=\{1\} style=\{styles\.planPriceChipLabel\}>\{price\}<\/Text>/);
  assertSourceMatch(planCard, /\{benefits\.map\(\(item, index\) =>/);
  assertSourceMatch(subscription, /<Text style=\{textStyles\.caption\}>Elige la modalidad de tu suscripción\.<\/Text>/);
  assertSourceMatch(planCard, /Free:[\s\S]*Hasta 12[\s\S]*Hasta 4[\s\S]*1 de hasta 2 semanas[\s\S]*Sin créditos incluidos/);
  assertSourceMatch(subscription, /<Text style=\{styles\.eyebrow\}>BOLSA DE CRÉDITOS<\/Text>\s*<Text style=\{styles\.productName\}>\{configured\.credits\.toLocaleString\("es-CL"\)\} créditos<\/Text>/);
  assertSourceMatch(subscription, /productName: \{[^}]*fontSize: 26[^}]*fontWeight: tokens\.weight\.extraBold/);
  assertSourceMatch(subscription, /const monthlyDisplayPrice = Platform\.OS === "android" \? monthlyAndroidOffer\?\.displayPrice : monthlyStoreProduct\?\.displayPrice/);
  assertSourceMatch(subscription, /planPriceChipLabel: \{[^}]*color: tokens\.color\.surfaceApp[^}]*fontSize: 16[^}]*fontVariant: \["tabular-nums"\][^}]*fontWeight: tokens\.weight\.semibold/);
  assertSourceMatch(planCard, /Basic:[\s\S]*entity: "food", label: "Alimentos", value: "Ilimitados"[\s\S]*label: "Comidas", value: "Ilimitadas"[\s\S]*label: "Planes diarios", value: "Ilimitados"[\s\S]*label: "Programas", value: "Ilimitados · hasta 12 semanas"[\s\S]*150 créditos al mes/);
  assertSourceMatch(planCard, /Pro:[\s\S]*Todo lo de Basic[\s\S]*1\.000 créditos al mes/);
  assertSourceDoesNotMatch(subscription, /label: "Publicación"|Contenido compatible|\bUpload\b/);
  assertSourceMatch(planCard, /benefitLabel: \{[^}]*fontSize: 14/);
  assertSourceMatch(planCard, /benefitValue: \{[^}]*fontSize: 14[^}]*textAlign: "right"/);
  assertSourceMatch(planCard, /item\.entity \? <EntityIcon entity=\{item\.entity\} size="benefit" \/>/);
  assertSourceMatch(planCard, /entity: "meal", label: "Comidas"/);
  assertSourceMatch(planCard, /entity: "dailyPlan", label: "Planes diarios"/);
  assertSourceMatch(planCard, /entity: "program", label: "Programas"/);
  assertSourceMatch(subscription, /const interval = configured\.interval === "year" \? "Anual" : "Mensual"/);
  assertSourceMatch(subscription, /numericPrice \/ \(monthlyNumericPrice \* 12\)/);
  assertSourceMatch(subscription, /`\$\{price\}\/año\$\{annualDiscount > 0 \? ` · Ahorra \$\{annualDiscount\}%` : ""\}`/);
  assertSourceMatch(subscription, /label=\{`\$\{interval\} · \$\{priceExplanation\}`\}/);
  assertSourceMatch(subscription, /<SubscriptionPurchaseButton[\s\S]*label=\{`\$\{interval\} · \$\{priceExplanation\}`\}/);
  assertSourceMatch(subscription, /<SubscriptionPurchaseButton[\s\S]*label=\{`Comprar \$\{configured\.credits\.toLocaleString\("es-CL"\)\} créditos`\}/);
  assertSourceMatch(planCard, /LinearGradient id="subscription-purchase-macros"[\s\S]*tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat/);
  assertSourceMatch(subscription, /<CreditPackPriceChip label=\{storeProduct\?\.displayPrice \?\? "Consultando…"\} \/>/);
  assertSourceMatch(subscription, /LinearGradient id="credit-pack-price-macros"[\s\S]*tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat/);
  assertSourceDoesNotMatch(subscription, /subscription-card-macros|SubscriptionCardAccent/);
  assertSourceDoesNotMatch(subscription, /label=\{`Suscribirme a \$\{configured\.plan_name\}`\}/);
  assertSourceDoesNotMatch(subscription, /getStorefront\(\)/);
  assertSourceDoesNotMatch(subscription, /Diagnóstico App Store: tienda/);
});

test("App Store purchases recover a completed StoreKit transaction before reporting failure", async () => {
  const subscription = await readTestFile(path.resolve(process.cwd(), "src/app/subscription.tsx"), "utf8");
  const packageManifest = JSON.parse(
    await readTestFile(path.resolve(process.cwd(), "package.json"), "utf8"),
  ) as { dependencies?: Record<string, string> };

  assert.equal(packageManifest.dependencies?.["expo-iap"], "^5.5.1");
  assertSourceMatch(subscription, /getAvailablePurchases\(\{/);
  assertSourceMatch(subscription, /purchase\.productId === productId/);
  assertSourceMatch(subscription, /for \(const purchase of matching\) await submitPurchase\(purchase\)/);
  assertSourceMatch(subscription, /No se realizó ningún cobro/);
});

test("restore purchases explains when no store transaction is pending and reports incomplete verification", async () => {
  const subscription = await readTestFile(path.resolve(process.cwd(), "src/app/subscription.tsx"), "utf8");

  assertSourceMatch(subscription, /if \(recovered\.length === 0\)/);
  assertSourceMatch(subscription, /await restorePurchases\(\);\s+const recovered = await getAvailablePurchases\(\)/);
  assertSourceMatch(subscription, /if \(!restoring\.current\)/);
  assertSourceMatch(subscription, /No hay compras pendientes de restaurar/);
  assertSourceMatch(subscription, /if \(await submitPurchase\(purchase\)\) restored \+= 1/);
  assertSourceMatch(subscription, /restored === recovered\.length/);
  assertSourceMatch(subscription, /No pudimos verificar todas las compras disponibles/);
});
