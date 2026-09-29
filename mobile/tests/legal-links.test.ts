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

  assertSourceMatch(subscription, /apple_app_store: "App Store"/);
  assertSourceMatch(subscription, /google_play: "Google Play"/);
  assertSourceMatch(subscription, /paddle: "Paddle"/);
  assertSourceDoesNotMatch(subscription, /mercado_pago: "Mercado Pago"/);
  assertSourceMatch(subscription, /Precio oficial de \$\{Platform\.OS === "android" \? "Google Play" : "App Store"\}/);
  assertSourceMatch(subscription, /detail=\{Platform\.OS === "android" \? "Google Play" : "App Store"\}/);
  assertSourceMatch(subscription, /title="Canales de cobro registrados"/);
  assertSourceMatch(subscription, /no cambian la tienda de las compras nuevas mostradas arriba/);
  assertSourceDoesNotMatch(subscription, /detail="Precio oficial de App Store"/);
  assertSourceMatch(subscription, /productStatusAndroid === "not-found"/);
  assertSourceMatch(subscription, /androidUnavailable \? "No disponible" : "Consultando…"/);
  assertSourceMatch(subscription, /getStorefront\(\)/);
  assertSourceMatch(subscription, /appConfig\.deploymentEnvironment === "staging"/);
  assertSourceMatch(subscription, /Diagnóstico App Store: tienda/);
  assertSourceMatch(subscription, /products\[0\]\?\.currency \?\? subscriptions\[0\]\?\.currency/);
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
