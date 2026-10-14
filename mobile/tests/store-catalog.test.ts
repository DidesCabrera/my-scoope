import assert from "node:assert/strict";
import test from "node:test";
import { StoreCatalog } from "../src/billing/store-catalog";

type Product = { id: string; displayPrice: string; currency: string };
const usd: Product = { id: "pro.monthly", displayPrice: "$5.99", currency: "USD" };
const clp: Product = { id: "pro.monthly", displayPrice: "$6.990", currency: "CLP" };

test("a storefront refresh replaces existing IDs, including subscriptions and packs", async () => {
  let products = [usd, { ...usd, id: "credits.500" }];
  let storefront = "USA";
  const catalog = new StoreCatalog({ storefront: async () => storefront, fetch: async () => products });
  await catalog.refresh(["pro.monthly", "credits.500"]);
  storefront = "CHL";
  products = [clp, { ...clp, id: "credits.500" }];
  await catalog.refresh(["pro.monthly", "credits.500"]);
  assert.deepEqual(catalog.state.items, products);
  assert.equal(catalog.state.loading, false);
});

test("a storefront change during a native query discards the old quote and refetches once", async () => {
  let storefront = "USA";
  let queries = 0;
  const catalog = new StoreCatalog({
    storefront: async () => storefront,
    fetch: async () => { queries += 1; storefront = "CHL"; return [queries === 1 ? usd : clp]; },
  });
  assert.deepEqual(await catalog.refresh(["pro.monthly"]), [clp]);
  assert.equal(queries, 2);
});

test("a late response cannot overwrite newer prices and failed queries remove stale purchase controls", async () => {
  let first: ((products: Product[]) => void) | undefined;
  let queries = 0;
  const catalog = new StoreCatalog<Product>({
    storefront: async () => "CHL",
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
  const catalog = new StoreCatalog({ storefront: async () => "CHL", fetch: async () => [clp, { ...clp, id: "retired" }] });
  assert.deepEqual(await catalog.refresh(["pro.monthly"]), [clp]);
  const next = catalog.refresh(["pro.monthly"]);
  catalog.dispose();
  assert.equal(await next, null);
});
