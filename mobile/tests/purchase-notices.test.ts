import assert from "node:assert/strict";
import test from "node:test";
import type { EntitlementsData, SubscriptionData } from "../src/api/billing-types";
import { PurchaseCoordinator, type StorePurchase } from "../src/billing/purchase-coordinator";

const monthly = "pro.monthly";
const annual = "pro.annual";
const current: SubscriptionData = {
  eligible: true, purchases_enabled: true, can_buy_credit_packs: true,
  app_account_token: "account-a", google_obfuscated_account_id: "google-a", plan_name: "Pro", status: "active",
  products: [monthly, annual].map((product_id) => ({ product_id, provider: "apple_app_store", plan_name: "Pro", interval: product_id === annual ? "year" : "month", base_plan_id: "" })),
  credit_packs: [], duplicate_active_providers: false,
  evidence: [{ provider: "apple_app_store", status: "authorized", period_end: null, product_id: monthly }],
};
const credits: EntitlementsData = { plan_name: "Pro", plan_slug: "pro", subscription_status: "active", period: "2026-10",
  available_credits: 2000, included_monthly_credits: 1000, purchased_credits: 1000, reserved_credits: 0,
  monthly_credit_limit: 1000, daily_credit_limit: 0, workspace_limits: {}, workspace_usage: {} };
const receipt: StorePurchase = { id: "pro-receipt", productId: monthly, purchaseToken: "jws", purchaseState: "purchased", appAccountToken: "account-a", transactionDate: 2000 };

async function fixture(post?: () => Promise<unknown>) {
  let finishes = 0;
  const coordinator = new PurchaseCoordinator({ provider: "apple_app_store", now: () => 1000, errorMessage: String,
    finish: async () => { finishes += 1; },
    apiRequest: async <T,>(path: string, init?: RequestInit): Promise<T> => (
      init?.method === "POST" ? post ? await post() : { ...current, entitlements: credits }
        : path.endsWith("/entitlements") ? credits : current
    ) as T,
  });
  await coordinator.refresh();
  return { coordinator, finishes: () => finishes };
}

test("a fresh requested purchase confirms once; restore and a background receipt never repeat it", async () => {
  const f = await fixture();
  assert.equal(f.coordinator.begin(monthly), true);
  await f.coordinator.submit(receipt);
  assert.equal(f.coordinator.state.message, "Tu plan Pro ya está activo.");
  f.coordinator.clearMessages();
  await f.coordinator.submit(receipt, true, "restore");
  await f.coordinator.submit({ ...receipt, id: "renewal" }, false, "recovery");
  await f.coordinator.reconcile();
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.coordinator.state.entitlements?.available_credits, 2000);
  assert.equal(f.finishes(), 2);
  f.coordinator.dispose();
});

test("an existing monthly receipt cannot turn a cancelled annual sheet into an activation message", async () => {
  const f = await fixture();
  assert.equal(f.coordinator.begin(annual), true);
  await f.coordinator.submit({ ...receipt, transactionDate: 500 }, false, "event");
  assert.equal(f.coordinator.state.phase, "store");
  assert.equal(f.coordinator.state.productId, annual);
  f.coordinator.storeFailed(null);
  await f.coordinator.submit({ ...receipt, id: "old-replay", transactionDate: 500 }, false, "event");
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.coordinator.state.error, null);
  assert.equal(f.coordinator.state.entitlements?.plan_name, "Pro");
  f.coordinator.dispose();
});

test("a historical receipt for the same SKU is not a new purchase, including native verification failure", async () => {
  const f = await fixture(async () => { throw new Error("offline"); });
  f.coordinator.begin(monthly);
  await f.coordinator.submit({ ...receipt, transactionDate: 500 });
  assert.equal(f.coordinator.state.phase, "store");
  f.coordinator.storeFailed(null);
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.coordinator.state.busy, false);
  f.coordinator.dispose();
});

test("a concurrent automatic renewal is verified quietly while a same-SKU purchase sheet is open", async () => {
  const f = await fixture();
  f.coordinator.begin(monthly);
  await f.coordinator.submit({ ...receipt, transactionReasonIOS: "RENEWAL" });
  assert.equal(f.coordinator.state.phase, "store");
  f.coordinator.storeFailed(null);
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.finishes(), 1);
  f.coordinator.dispose();
});

test("leaving the screen while verification is running prevents a late transient message", async () => {
  let release: ((value: unknown) => void) | undefined;
  const f = await fixture(() => new Promise((resolve) => { release = resolve; }));
  f.coordinator.begin(monthly);
  const pending = f.coordinator.submit(receipt);
  await new Promise((resolve) => setImmediate(resolve));
  f.coordinator.clearMessages();
  release!({ ...current, entitlements: credits });
  await pending;
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.coordinator.state.phase, "active");
  assert.equal(f.finishes(), 1);
  f.coordinator.dispose();
});

test("a store-confirmed scheduled change shows its renewal date without claiming activation", async () => {
  const scheduled = { ...current, evidence: [{ ...current.evidence[0], next_product_id: annual, period_end: "2026-11-10T12:00:00Z" }] };
  const f = await fixture(async () => ({ ...scheduled, entitlements: credits }));
  f.coordinator.begin(annual);
  await f.coordinator.reconcile(true);
  assert.equal(f.coordinator.state.phase, "scheduled");
  assert.match(f.coordinator.state.message ?? "", /noviembre/);
  assert.doesNotMatch(f.coordinator.state.message ?? "", /ya está activo/);
  f.coordinator.dispose();
});

test("reconciliation does not announce an already scheduled change as a new request", async () => {
  const scheduled = { ...current, evidence: [{ ...current.evidence[0], next_product_id: annual, period_end: "2026-11-10T12:00:00Z" }] };
  const coordinator = new PurchaseCoordinator({ provider: "apple_app_store", now: () => 1000, errorMessage: String,
    finish: async () => undefined,
    apiRequest: async <T,>(path: string, init?: RequestInit): Promise<T> => (
      init?.method === "POST" ? { ...scheduled, entitlements: credits } : path.endsWith("/entitlements") ? credits : scheduled
    ) as T,
  });
  await coordinator.refresh();
  coordinator.begin(annual);
  await coordinator.reconcile(true);
  assert.equal(coordinator.state.phase, "scheduled");
  assert.equal(coordinator.state.message, null);
  coordinator.dispose();
});
