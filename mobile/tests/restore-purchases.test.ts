import assert from "node:assert/strict";
import test from "node:test";
import { restoreAccountPurchases } from "../src/billing/restore-purchases";
import type { StorePurchase } from "../src/billing/purchase-coordinator";

const subscription: StorePurchase = { id: "sub", productId: "basic", purchaseToken: "jws", purchaseState: "purchased" };
const consumable: StorePurchase = { ...subscription, id: "credits", productId: "credits" };

test("restore includes unfinished consumables and deduplicates subscription receipts", async () => {
  const calls: string[] = [];
  const result = await restoreAccountPurchases({
    synchronize: async () => { calls.push("sync"); },
    available: async () => [subscription], pending: async () => [consumable, subscription],
    submit: async (purchase, retry) => { assert.equal(retry, true); calls.push(purchase.id); return true; },
    refresh: async () => { calls.push("refresh"); },
  });
  assert.deepEqual(result, { found: 2, verified: 2 });
  assert.deepEqual(calls, ["sync", "credits", "sub", "refresh"]);
});

test("native sync failure never reports an empty successful restore", async () => {
  let reads = 0;
  await assert.rejects(restoreAccountPurchases({ synchronize: async () => { throw new Error("store offline"); },
    available: async () => { reads++; return []; }, pending: async () => [], submit: async () => true, refresh: async () => undefined,
  }), /store offline/);
  assert.equal(reads, 0);
});

test("an empty restore still refreshes entitlements, and partial verification is explicit", async () => {
  let refreshes = 0;
  const dependencies = { synchronize: async () => undefined, available: async () => [], pending: async () => [],
    submit: async () => false, refresh: async () => { refreshes++; } };
  assert.deepEqual(await restoreAccountPurchases(dependencies), { found: 0, verified: 0 });
  assert.deepEqual(await restoreAccountPurchases({ ...dependencies, available: async () => [subscription] }), { found: 1, verified: 0 });
  assert.equal(refreshes, 2);
});
