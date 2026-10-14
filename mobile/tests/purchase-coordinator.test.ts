import assert from "node:assert/strict";
import test from "node:test";
import type { EntitlementsData, SubscriptionData } from "../src/api/billing-types";
import { PurchaseCoordinator, type StorePurchase } from "../src/billing/purchase-coordinator";

const basicId = "basic.monthly";
const proId = "pro.monthly";
function entitlements(name: string): EntitlementsData {
  return { plan_name: name, plan_slug: name.toLowerCase(), subscription_status: "Active", period: "2026-10",
    available_credits: 150, reserved_credits: 0, monthly_credit_limit: 150, daily_credit_limit: 0,
    included_monthly_credits: 150, purchased_credits: 0, workspace_limits: {}, workspace_usage: {} };
}
function overview(name = "Basic", product = basicId): SubscriptionData {
  return { eligible: true, purchases_enabled: true, app_account_token: "account-a", google_obfuscated_account_id: "google-a",
    plan_name: name, status: "active", products: [
      { product_id: basicId, provider: "apple_app_store", plan_name: "Basic", interval: "month", base_plan_id: "" },
      { product_id: proId, provider: "apple_app_store", plan_name: "Pro", interval: "month", base_plan_id: "" },
      { product_id: "basic.annual", provider: "apple_app_store", plan_name: "Basic", interval: "year", base_plan_id: "" },
    ], credit_packs: [{ product_id: "pack", provider: "apple_app_store", credits: 500, amount_minor: 100, currency: "CLP" }],
    can_buy_credit_packs: true, duplicate_active_providers: false,
    evidence: [{ provider: "apple_app_store", status: "authorized", period_end: null, product_id: product }] };
}
const purchase: StorePurchase = { id: "receipt-1", productId: proId, purchaseToken: "signed-receipt", purchaseState: "purchased", appAccountToken: "account-a" };
async function fixture(options: { provider?: "apple_app_store" | "google_play"; post?: (path: string) => Promise<unknown>; finish?: () => Promise<void>; wait?: (ms: number) => Promise<void> } = {}) {
  const calls: string[] = [];
  let server = overview();
  let serverCredits = entitlements(server.plan_name);
  const coordinator = new PurchaseCoordinator({ provider: options.provider ?? "apple_app_store", errorMessage: String,
    finish: async (_purchase, consumable) => { calls.push(`finish:${consumable}`); await options.finish?.(); },
    wait: options.wait ?? (async () => undefined),
    apiRequest: async <T,>(path: string, init?: RequestInit): Promise<T> => {
      calls.push(`${init?.method ?? "GET"}:${path}:${init?.cache ?? "default"}`);
      if (init?.method === "POST") return (options.post ? await options.post(path) : { ...overview("Pro", proId), entitlements: entitlements("Pro") }) as T;
      return (path.endsWith("/entitlements") ? serverCredits : server) as T;
    },
  });
  await coordinator.refresh();
  calls.length = 0;
  return { coordinator, calls, setServer: (next: SubscriptionData, credits = entitlements(next.plan_name)) => { server = next; serverCredits = credits; } };
}
const flush = () => new Promise((resolve) => setImmediate(resolve));

test("an upgrade exposes the accepted benefits before completion, with one POST and no polling", async () => {
  const f = await fixture();
  assert.equal(f.coordinator.begin(proId), true);
  assert.equal(await f.coordinator.submit(purchase), true);
  assert.equal(f.coordinator.state.phase, "active");
  assert.equal(f.coordinator.state.entitlements?.plan_name, "Pro");
  assert.deepEqual(f.calls, ["POST:/api/v1/subscriptions/apple/transactions:default", "finish:false"]);
  f.coordinator.dispose();
});

test("native event and promise share one verification; distinct receipts run serially", async () => {
  let release!: (value: unknown) => void;
  const f = await fixture({ post: () => new Promise((resolve) => { release = resolve; }) });
  const one = f.coordinator.submit(purchase);
  assert.equal(f.coordinator.submit(purchase, true), one);
  await flush();
  const two = f.coordinator.submit({ ...purchase, id: "receipt-2" });
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 1);
  release({ ...overview("Pro", proId), entitlements: entitlements("Pro") });
  await one;
  await flush();
  release({ ...overview("Pro", proId), entitlements: entitlements("Pro") });
  await two;
  assert.equal(f.calls.filter((call) => call === "finish:false").length, 2);
  f.coordinator.dispose();
});

test("verification failure retains receipt and never finishes; explicit restore retries", async () => {
  let failures = 1;
  const f = await fixture({ post: async () => {
    if (failures--) throw new Error("offline");
    return { ...overview("Pro", proId), entitlements: entitlements("Pro") };
  } });
  assert.equal(await f.coordinator.submit(purchase), false);
  assert.equal(f.coordinator.state.phase, "pending");
  assert.equal(f.coordinator.begin(proId), false);
  await f.coordinator.submit(purchase);
  assert.equal(f.calls.length, 1);
  assert.equal(await f.coordinator.submit(purchase, true), true);
  assert.equal(f.coordinator.state.phase, "active");
  f.coordinator.dispose();
});

test("pending approval and another account's receipt cannot grant or finish anything", async () => {
  const f = await fixture();
  assert.equal(await f.coordinator.submit({ ...purchase, purchaseState: "pending" }), false);
  assert.equal(await f.coordinator.submit({ ...purchase, appAccountToken: "account-b" }), false);
  assert.deepEqual(f.calls, []);
  f.coordinator.dispose();
});

test("a finish failure preserves active benefits and retries completion without another POST", async () => {
  let failures = 1;
  const f = await fixture({ finish: async () => { if (failures--) throw new Error("store offline"); } });
  await f.coordinator.submit(purchase);
  assert.equal(f.coordinator.state.phase, "active");
  assert.equal(f.coordinator.state.finishPending, true);
  f.setServer(overview("Pro", proId));
  await f.coordinator.submit(purchase, true);
  assert.equal(f.coordinator.state.phase, "active");
  assert.equal(f.coordinator.state.finishPending, false);
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 1);
  f.coordinator.dispose();
});

test("retrying an accepted receipt after a refund uses current benefits instead of cached success", async () => {
  let failures = 1;
  const f = await fixture({ finish: async () => { if (failures--) throw new Error("completion failed"); } });
  await f.coordinator.submit(purchase);
  const current = overview("Free", proId);
  current.status = "canceled";
  current.evidence[0].status = "canceled";
  f.setServer(current, { ...entitlements("Free"), available_credits: 0, credit_status: "ready" });
  await f.coordinator.submit(purchase, true);
  assert.equal(f.coordinator.state.phase, "idle");
  assert.equal(f.coordinator.state.entitlements?.plan_name, "Free");
  assert.equal(f.coordinator.state.finishPending, false);
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 1);
  f.coordinator.dispose();
});

test("finishing another receipt does not hide an earlier unfinished accepted transaction", async () => {
  let finishes = 0;
  const f = await fixture({ finish: async () => { if (++finishes === 1) throw new Error("first completion failed"); } });
  await f.coordinator.submit(purchase);
  await f.coordinator.submit({ ...purchase, id: "second-receipt" });
  assert.equal(f.coordinator.state.finishPending, true);
  f.setServer(overview("Pro", proId));
  await f.coordinator.submit(purchase, true);
  assert.equal(f.coordinator.state.finishPending, false);
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 2);
  f.coordinator.dispose();
});

test("same-plan annual change is scheduled when renewal evidence says so, without activation polling", async () => {
  const snapshot = overview();
  snapshot.evidence[0].next_product_id = "basic.annual";
  const f = await fixture({ post: async () => ({ ...snapshot, entitlements: entitlements("Basic") }) });
  await f.coordinator.submit({ ...purchase, productId: "basic.annual" });
  assert.equal(f.coordinator.state.phase, "scheduled");
  assert.equal(f.calls.length, 2);
  f.coordinator.dispose();
});

test("bounded activation rechecks both fresh contracts and stops with a recoverable pending state", async () => {
  const delays: number[] = [];
  const f = await fixture({ post: async () => ({ ...overview(), entitlements: entitlements("Basic") }),
    wait: async (ms) => { delays.push(ms); } });
  await f.coordinator.submit(purchase);
  await flush();
  assert.equal(f.coordinator.state.phase, "pending");
  assert.deepEqual(delays, [1500, 3000, 6000, 12000]);
  assert.equal(f.calls.filter((call) => call.startsWith("GET")).length, 8);
  assert.ok(f.calls.filter((call) => call.startsWith("GET")).every((call) => call.endsWith(":no-store")));
  f.setServer(overview("Pro", proId));
  await f.coordinator.refresh();
  assert.equal(f.coordinator.state.phase, "active");
  f.coordinator.dispose();
});

test("consumable completion follows settlement, including a refund tombstone", async () => {
  for (const status of ["approved", "refunded"] as const) {
    const f = await fixture({ post: async () => ({ ...entitlements("Basic"), purchase_status: status }) });
    await f.coordinator.submit({ ...purchase, productId: "pack" });
    assert.equal(f.coordinator.state.phase, status === "approved" ? "credited" : "refunded");
    assert.deepEqual(f.calls, ["POST:/api/v1/credit-packs/apple/transactions:default", "finish:true"]);
    f.coordinator.dispose();
  }
});

test("retrying consumable completion refreshes the balance and preserves an acknowledged refund", async () => {
  for (const purchase_status of ["approved", "refunded"] as const) {
    let failures = 1;
    const f = await fixture({ post: async () => ({ ...entitlements("Basic"), purchase_status }),
      finish: async () => { if (failures--) throw new Error("completion failed"); } });
    const pack = { ...purchase, productId: "pack" };
    await f.coordinator.submit(pack);
    f.setServer(overview(), { ...entitlements("Basic"), available_credits: 125, credit_status: "ready" });
    await f.coordinator.submit(pack, true);
    assert.equal(f.coordinator.state.phase, purchase_status === "approved" ? "credited" : "refunded");
    assert.equal(f.coordinator.state.entitlements?.available_credits, 125);
    assert.equal(f.coordinator.state.finishPending, false);
    assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 1);
    f.coordinator.dispose();
  }
});

test("logout during acceptance prevents late UI updates and completion under another account", async () => {
  let release!: (value: unknown) => void;
  const f = await fixture({ post: () => new Promise((resolve) => { release = resolve; }) });
  const task = f.coordinator.submit(purchase);
  await flush();
  const previous = f.coordinator.state;
  f.coordinator.dispose();
  release({ ...overview("Pro", proId), entitlements: entitlements("Pro") });
  await task;
  assert.equal(f.coordinator.state, previous);
  assert.equal(f.calls.length, 1);
});

test("late store failures do not undo accepted benefits", async () => {
  const f = await fixture();
  await f.coordinator.submit(purchase);
  f.coordinator.storeFailed("late error");
  assert.equal(f.coordinator.state.phase, "active");
  f.coordinator.dispose();
});

test("cancellation closes silently, and pending approval releases the purchase controls", async () => {
  const f = await fixture();
  f.coordinator.begin(proId);
  f.coordinator.storeFailed(null);
  assert.equal(f.coordinator.state.busy, false);
  assert.equal(f.coordinator.state.error, null);
  assert.equal(f.coordinator.begin(proId), true);
  await f.coordinator.submit({ ...purchase, purchaseState: "pending" });
  assert.equal(f.coordinator.state.busy, false);
  assert.equal(f.coordinator.state.phase, "idle");
  assert.deepEqual(f.calls, []);
  f.coordinator.dispose();
});

test("a purchased receipt without its signed token remains recoverable rather than spinning forever", async () => {
  const f = await fixture();
  f.coordinator.begin(proId);
  await f.coordinator.submit({ ...purchase, purchaseToken: null });
  assert.equal(f.coordinator.state.busy, false);
  assert.equal(f.coordinator.state.phase, "pending");
  assert.deepEqual(f.calls, []);
  f.coordinator.dispose();
});

test("a request deadline leaves the transaction unfinished and offers verification retry", async () => {
  let finished = 0;
  const coordinator = new PurchaseCoordinator({ provider: "apple_app_store", errorMessage: String,
    requestTimeoutMs: 5, finish: async () => { finished++; },
    apiRequest: async <T,>(path: string, init?: RequestInit): Promise<T> => {
      if (init?.method !== "POST") return (path.endsWith("/entitlements") ? entitlements("Basic") : overview()) as T;
      return new Promise<T>((_resolve, reject) => init.signal?.addEventListener("abort", () => reject(new Error("timeout")), { once: true }));
    },
  });
  await coordinator.refresh();
  coordinator.begin(proId);
  assert.equal(await coordinator.submit(purchase), false);
  assert.equal(coordinator.state.phase, "pending");
  assert.equal(finished, 0);
  coordinator.dispose();
});

test("server-confirmed deferred changes release controls after one reconciliation", async () => {
  const f = await fixture({ post: async () => {
    const current = overview();
    current.evidence[0].next_product_id = "basic.annual";
    return { ...current, entitlements: entitlements("Basic") };
  } });
  f.coordinator.begin("basic.annual");
  await Promise.all([f.coordinator.reconcile(), f.coordinator.reconcile()]);
  assert.equal(f.coordinator.state.phase, "scheduled");
  assert.equal(f.coordinator.state.busy, false);
  assert.equal(f.calls.length, 1);
  f.coordinator.dispose();
});

test("older subscription and consumable callbacks preserve an unfinished requested upgrade", async () => {
  let subscriptionPosts = 0;
  const f = await fixture({ post: async (path) => {
    if (path.includes("credit-packs")) return { ...entitlements("Basic"), purchase_status: "approved" };
    if (++subscriptionPosts === 1) throw new Error("offline after Apple approval");
    return subscriptionPosts === 2 ? { ...overview(), entitlements: entitlements("Basic") }
      : { ...overview("Pro", proId), entitlements: entitlements("Pro") };
  } });
  f.coordinator.begin(proId);
  assert.equal(await f.coordinator.submit(purchase), false);
  await f.coordinator.submit({ ...purchase, id: "old-basic", productId: basicId });
  await flush();
  assert.equal(f.coordinator.state.productId, proId);
  assert.equal(f.coordinator.state.planName, "Pro");
  assert.equal(f.coordinator.state.phase, "pending");
  await f.coordinator.submit({ ...purchase, id: "old-pack", productId: "pack" });
  await flush();
  assert.equal(f.coordinator.state.productId, proId);
  assert.equal(f.coordinator.state.phase, "pending");
  assert.equal(await f.coordinator.submit(purchase, true), true);
  assert.equal(f.coordinator.state.phase, "active");
  f.coordinator.dispose();
});

test("restoring superseded or expired evidence acknowledges it without waiting for obsolete benefits", async () => {
  for (const transaction_status of ["superseded", "inactive"] as const) {
    const current = overview(transaction_status === "inactive" ? "Free" : "Pro", proId);
    if (transaction_status === "inactive") current.status = "expired";
    const f = await fixture({ post: async () => ({ ...current, entitlements: entitlements(current.plan_name), transaction_status }) });
    await f.coordinator.submit({ ...purchase, productId: basicId });
    assert.equal(f.coordinator.state.phase, "idle");
    assert.equal(f.coordinator.state.entitlements?.plan_name, current.plan_name);
    assert.equal(f.coordinator.state.busy, false);
    assert.equal(f.calls.length, 2);
    f.coordinator.dispose();
  }
});

test("a scheduled change notice disappears when renewal is cancelled", async () => {
  const current = overview();
  current.evidence[0].next_product_id = "basic.annual";
  const f = await fixture({ post: async () => ({ ...current, entitlements: entitlements("Basic") }) });
  await f.coordinator.submit({ ...purchase, productId: "basic.annual" });
  assert.equal(f.coordinator.state.phase, "scheduled");
  current.evidence[0].cancel_at_period_end = true;
  f.setServer(current);
  await f.coordinator.refresh();
  assert.equal(f.coordinator.state.phase, "idle");
  assert.equal(f.coordinator.state.message, null);
  assert.equal(f.coordinator.state.entitlements?.plan_name, "Basic");
  f.coordinator.dispose();
});

test("upgrade success waits for spendable credits while a prior reservation or freeze blocks them", async () => {
  for (const credit_status of ["pending_reservation", "frozen"] as const) {
    const current = overview("Pro", proId);
    const blocked = { ...entitlements("Pro"), available_credits: 0, reserved_credits: 10, credit_status };
    const f = await fixture({ post: async () => ({ ...current, entitlements: blocked }) });
    f.coordinator.begin(proId);
    f.setServer(current, blocked);
    await f.coordinator.submit(purchase);
    await flush();
    assert.equal(f.coordinator.state.phase, "pending");
    assert.equal(f.coordinator.state.entitlements?.available_credits, 0);
    assert.equal(f.coordinator.begin(proId), false);
    f.setServer(current, { ...entitlements("Pro"), available_credits: 1000, credit_status: "ready" });
    await f.coordinator.refresh();
    assert.equal(f.coordinator.state.phase, "active");
    f.coordinator.dispose();
  }
});

test("a consumable confirms its balance only after a prior reservation is released", async () => {
  const blocked = { ...entitlements("Basic"), available_credits: 0, reserved_credits: 10, credit_status: "pending_reservation" as const };
  const f = await fixture({ post: async () => ({ ...blocked, purchase_status: "approved" }) });
  f.setServer(overview(), blocked);
  await f.coordinator.submit({ ...purchase, productId: "pack" });
  await flush();
  assert.equal(f.coordinator.state.phase, "pending");
  assert.equal(f.calls.filter((call) => call === "finish:true").length, 1);
  f.setServer(overview(), { ...entitlements("Basic"), available_credits: 650, credit_status: "ready" });
  await f.coordinator.refresh();
  assert.equal(f.coordinator.state.phase, "credited");
  assert.equal(f.coordinator.state.entitlements?.available_credits, 650);
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 1);
  f.coordinator.dispose();
});

test("retired mapped consumables can finish while the purchase controls do not offer them", async () => {
  const f = await fixture({ post: async () => ({ ...entitlements("Basic"), purchase_status: "approved" }) });
  const current = overview();
  current.transaction_products = [{ product_id: "retired.pack", provider: "apple_app_store", kind: "credit_pack", plan_name: "" }];
  f.setServer(current);
  await f.coordinator.refresh();
  f.calls.length = 0;
  assert.equal(f.coordinator.begin("retired.pack"), false);
  assert.equal(await f.coordinator.submit({ ...purchase, productId: "retired.pack" }), true);
  assert.equal(f.coordinator.state.phase, "credited");
  assert.deepEqual(f.calls, ["POST:/api/v1/credit-packs/apple/transactions:default", "finish:true"]);
  f.coordinator.dispose();
});

test("new transaction IDs for the same consumable settle and finish independently", async () => {
  const f = await fixture({ post: async () => ({ ...entitlements("Basic"), purchase_status: "approved" }) });
  await f.coordinator.submit({ ...purchase, id: "pack-1", productId: "pack" });
  await f.coordinator.submit({ ...purchase, id: "pack-2", productId: "pack" });
  assert.equal(f.calls.filter((call) => call.startsWith("POST")).length, 2);
  assert.equal(f.calls.filter((call) => call === "finish:true").length, 2);
  f.coordinator.dispose();
});

test("Google Play follows the same verified-benefits and completion ordering", async () => {
  const current = overview("Pro", proId);
  current.products.forEach((row) => { row.provider = "google_play"; });
  current.evidence[0].provider = "google_play";
  const f = await fixture({ provider: "google_play", post: async () => ({ ...current, entitlements: entitlements("Pro") }) });
  f.setServer(current);
  await f.coordinator.refresh();
  f.calls.length = 0;
  assert.equal(f.coordinator.begin(proId), true);
  await f.coordinator.submit({ ...purchase, appAccountToken: undefined });
  assert.equal(f.coordinator.state.phase, "active");
  assert.deepEqual(f.calls, ["POST:/api/v1/subscriptions/google-play/purchases:default", "finish:false"]);
  f.coordinator.dispose();
});
