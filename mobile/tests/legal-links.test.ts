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
