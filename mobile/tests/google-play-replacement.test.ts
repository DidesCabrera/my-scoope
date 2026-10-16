import assert from "node:assert/strict";
import test from "node:test";

import type { SubscriptionData } from "../src/api/billing-types";
import { googlePlayReplacement } from "../src/billing/google-play-replacement";

function overview(activeProduct?: string): SubscriptionData {
  return {
    eligible: true, purchases_enabled: true, app_account_token: "",
    google_obfuscated_account_id: "account-token", plan_name: activeProduct === "myscoope_pro" ? "Pro" : "Basic",
    status: activeProduct ? "active" : "none",
    products: [
      { product_id: "myscoope_basic", provider: "google_play", base_plan_id: "monthly", plan_name: "Basic", interval: "month" },
      { product_id: "myscoope_pro", provider: "google_play", base_plan_id: "monthly", plan_name: "Pro", interval: "month" },
    ],
    credit_packs: [], can_buy_credit_packs: false,
    evidence: activeProduct ? [{ provider: "google_play", status: "authorized", period_end: null, product_id: activeProduct }] : [],
    duplicate_active_providers: false,
  };
}

test("a first Google Play subscription has no replacement token", () => {
  assert.equal(googlePlayReplacement(overview(), [], "myscoope_basic", "monthly"), null);
});

test("an upgrade replaces Basic and a downgrade waits until renewal", () => {
  assert.deepEqual(googlePlayReplacement(
    overview("myscoope_basic"), [{ isActive: true, productId: "myscoope_basic", purchaseTokenAndroid: "old-basic" }], "myscoope_pro", "monthly",
  ), {
    purchaseToken: "old-basic",
    subscriptionProductReplacementParams: { oldProductId: "myscoope_basic", replacementMode: "charge-full-price" },
  });
  assert.equal(googlePlayReplacement(
    overview("myscoope_pro"), [{ isActive: true, productId: "myscoope_pro", purchaseTokenAndroid: "old-pro" }], "myscoope_basic", "monthly",
  )?.subscriptionProductReplacementParams.replacementMode, "deferred");
});

test("a backend subscription without its Play token cannot open another purchase", () => {
  assert.throws(() => googlePlayReplacement(overview("myscoope_basic"), [], "myscoope_pro", "monthly"), /Restaura las compras/);
});

test("an unlinked Play subscription cannot be charged through a different My Scoope account", () => {
  assert.throws(() => googlePlayReplacement(
    overview(), [{ isActive: true, productId: "myscoope_basic", purchaseTokenAndroid: "another-user" }], "myscoope_pro", "monthly",
  ), /otra cuenta/);
});

test("the same active base plan cannot be purchased again", () => {
  assert.throws(() => googlePlayReplacement(
    overview("myscoope_basic"), [{
      isActive: true, productId: "myscoope_basic", basePlanIdAndroid: "monthly", purchaseTokenAndroid: "old-basic",
    }], "myscoope_basic", "monthly",
  ), /Ya tienes activo/);
});
