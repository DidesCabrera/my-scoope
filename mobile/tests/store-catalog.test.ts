import assert from "node:assert/strict";
import test from "node:test";
import { StoreCatalog } from "../src/billing/store-catalog";
import type { StorefrontContext } from "../src/billing/storefront";

const usa: StorefrontContext = { id: "143441", countryCode: "USA", currency: "USD", environment: "sandbox", observedAt: 1 };
const chile: StorefrontContext = { id: "143483", countryCode: "CHL", currency: "CLP", environment: "sandbox", observedAt: 2 };

type Product = { id: string; displayPrice: string; currency: string };
const usd: Product = { id: "pro.monthly", displayPrice: "$5.99", currency: "USD" };
const clp: Product = { id: "pro.monthly", displayPrice: "$6.990", currency: "CLP" };

test("a storefront refresh replaces existing IDs, including subscriptions and packs", async () => {
  let products = [usd, { ...usd, id: "credits.500" }];
  let storefront = usa;
  const catalog = new StoreCatalog({ storefront: async () => storefront, fetch: async () => products });
  await catalog.refresh(["pro.monthly", "credits.500"]);
  storefront = chile;
  products = [clp, { ...clp, id: "credits.500" }];
  await catalog.refresh(["pro.monthly", "credits.500"]);
  assert.deepEqual(catalog.state.items, products);
  assert.equal(catalog.state.loading, false);
});

test("a storefront change during a native query discards the old quote and refetches once", async () => {
  let storefront = usa;
  let queries = 0;
  const catalog = new StoreCatalog({
    storefront: async () => storefront,
    fetch: async () => { queries += 1; storefront = chile; return [queries === 1 ? usd : clp]; },
  });
  assert.deepEqual(await catalog.refresh(["pro.monthly"]), [clp]);
  assert.equal(queries, 2);
});

test("a late response cannot overwrite newer prices and failed queries remove stale purchase controls", async () => {
  let first: ((products: Product[]) => void) | undefined;
  let queries = 0;
  const catalog = new StoreCatalog<Product>({
    storefront: async () => chile,
    fetch: async () => {
      queries += 1;
      if (queries === 1) return new Promise((resolve) => { first = resolve; });
      if (queries === 3) throw new Error("store offline");
      return [clp];
    },
  });
  const old = catalog.refresh(["pro.monthly"]);
  await new Promise((resolve) => setImmediate(resolve));
  await catalog.refresh(["pro.monthly"]);
  first!([usd]);
  assert.equal(await old, null);
  assert.deepEqual(catalog.state.items, [clp]);
  assert.equal(await catalog.refresh(["pro.monthly"]), null);
  assert.deepEqual(catalog.state, { items: [], loading: false, failed: true });
});

test("missing or retired products are not retained and account disposal ignores a late query", async () => {
  const catalog = new StoreCatalog({ storefront: async () => chile, fetch: async () => [clp, { ...clp, id: "retired" }] });
  assert.deepEqual(await catalog.refresh(["pro.monthly"]), [clp]);
  const next = catalog.refresh(["pro.monthly"]);
  catalog.dispose();
  assert.equal(await next, null);
});

test("a stable Chile/CLP storefront with USD native metadata is captured and never shown", async () => {
  let queries = 0;
  const catalog = new StoreCatalog({ storefront: async () => chile, fetch: async () => { queries += 1; return [{ ...usd, price: 5.99 }]; } });
  assert.equal(await catalog.refresh([usd.id], "foreground"), null);
  assert.equal(queries, 2);
  assert.deepEqual(catalog.state, { items: [], loading: false, failed: true });
  const sample = catalog.diagnostics.find((entry) => entry.result === "currency_mismatch")!;
  assert.equal(sample.after?.currency, "CLP");
  assert.equal(sample.products[0].currency, "USD");
  assert.equal(sample.products[0].price, 5.99);
  assert.equal(sample.products[0].displayPrice, "$5.99");
  assert.equal(sample.reason, "foreground");
});

test("delayed native prices get one refetch and retain Apple's exact display text", async () => {
  let queries = 0;
  const catalog = new StoreCatalog({ storefront: async () => chile, fetch: async () => [++queries === 1 ? usd : clp] });
  assert.deepEqual(await catalog.refresh([usd.id]), [clp]);
  assert.equal(catalog.diagnostics[0].result, "currency_mismatch");
  assert.equal(catalog.state.items[0].displayPrice, clp.displayPrice);
});

test("a storefront event invalidates pending quotes even if the country code stays the same", async () => {
  let release!: (items: Product[]) => void;
  const catalog = new StoreCatalog<Product>({ storefront: async () => chile, fetch: async () => new Promise((resolve) => { release = resolve; }) });
  const request = catalog.refresh([clp.id]);
  await new Promise((resolve) => setImmediate(resolve));
  catalog.invalidate();
  release([clp]);
  assert.equal(await request, null);
  assert.deepEqual(catalog.state.items, []);
  assert.equal(catalog.diagnostics.at(-1)?.result, "superseded");
});

test("other storefronts use native currency and quote text without a price table or conversion", async () => {
  for (const [countryCode, currency, displayPrice, price] of [["FRA", "EUR", "6,99 €", 6.99], ["JPN", "JPY", "￥1,000", 1000]] as const) {
    const product = { id: "pro.monthly", currency, displayPrice, price };
    const catalog = new StoreCatalog({ storefront: async () => ({ id: countryCode, countryCode, currency, environment: "sandbox", observedAt: 1 }), fetch: async () => [product] });
    assert.deepEqual(await catalog.refresh([product.id]), [product]);
    assert.equal(catalog.state.items[0].displayPrice, displayPrice);
  }
});

test("diagnostic history is bounded and only contains price metadata", async () => {
  const catalog = new StoreCatalog({ storefront: async () => chile, fetch: async () => [{ ...clp, purchaseToken: "private-receipt", appAccountToken: "private-account", debugDescription: "private-data" }] });
  for (let index = 0; index < 25; index += 1) await catalog.refresh([clp.id]);
  assert.equal(catalog.diagnostics.length, 20);
  assert.equal(JSON.stringify(catalog.diagnostics).includes("private-"), false);
});

for (const stalledRead of ["storefront_before", "products", "storefront_after"]) {
  test(`a stalled ${stalledRead} ends loading, ignores a late response and permits a fresh retry`, async () => {
    let expire!: () => void;
    let release!: () => void;
    let healthy = false;
    let storefrontReads = 0;
    let timerActive = false;
    const waiting = new Promise<void>((resolve) => { release = resolve; });
    const catalog = new StoreCatalog({
      storefront: async () => {
        storefrontReads += 1;
        if (!healthy && (stalledRead === "storefront_before" || stalledRead === "storefront_after" && storefrontReads === 2)) await waiting;
        return chile;
      },
      fetch: async () => { if (!healthy && stalledRead === "products") await waiting; return [clp]; },
      schedule: (run, delay) => {
        assert.equal(delay, 15_000);
        expire = run;
        timerActive = true;
        return () => { timerActive = false; };
      },
    });
    const pending = catalog.refresh([clp.id]);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(catalog.state.loading, true);
    expire();
    assert.equal(await pending, null);
    assert.deepEqual(catalog.state, { items: [], loading: false, failed: true });
    assert.equal(catalog.failureReason, "timeout");
    assert.equal(catalog.diagnostics.at(-1)?.result, "timed_out");
    assert.equal(timerActive, false);

    healthy = true;
    release();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(catalog.state, { items: [], loading: false, failed: true });
    assert.deepEqual(await catalog.refresh([clp.id], "manual_retry"), [clp]);
    assert.deepEqual(catalog.state, { items: [clp], loading: false, failed: false });
    assert.equal(catalog.failureReason, null);
    assert.equal(timerActive, false);
  });
}

test("one deadline bounds both attempts after a mismatched quote", async () => {
  let expire!: () => void;
  let queries = 0;
  let deadlines = 0;
  const catalog = new StoreCatalog<Product>({
    storefront: async () => chile,
    fetch: async () => ++queries === 1 ? [usd] : new Promise(() => undefined),
    schedule: (run) => { deadlines += 1; expire = run; return () => undefined; },
  });
  const pending = catalog.refresh([clp.id]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(queries, 2);
  assert.equal(deadlines, 1);
  expire();
  assert.equal(await pending, null);
  assert.equal(catalog.failureReason, "timeout");
  assert.equal(catalog.state.loading, false);
});

for (const action of ["invalidate", "dispose"] as const) {
  test(`${action} settles a stalled query and cancels its timer`, async () => {
    let timerActive = false;
    const catalog = new StoreCatalog<Product>({
      storefront: async () => chile,
      fetch: () => new Promise(() => undefined),
      schedule: () => { timerActive = true; return () => { timerActive = false; }; },
    });
    const pending = catalog.refresh([clp.id]);
    await new Promise((resolve) => setImmediate(resolve));
    catalog[action]();
    assert.equal(await pending, null);
    assert.equal(timerActive, false);
    assert.equal(catalog.failureReason, null);
    assert.deepEqual(catalog.state.items, []);
  });
}

test("an empty native catalog offers retry instead of accepting a permanent missing-price state", async () => {
  let products: Product[] = [];
  const catalog = new StoreCatalog({ storefront: async () => chile, fetch: async () => products });
  assert.equal(await catalog.refresh([clp.id]), null);
  assert.deepEqual(catalog.state, { items: [], loading: false, failed: true });
  assert.equal(catalog.failureReason, "unavailable");
  products = [clp];
  assert.deepEqual(await catalog.refresh([clp.id], "manual_retry"), [clp]);
  assert.equal(catalog.state.failed, false);
});
