import type { StorefrontContext } from "./storefront";

export type StoreCatalogState<Product> = { items: Product[]; loading: boolean; failed: boolean };
export type PriceDiagnostic = {
  loadedAt: number; reason: string; requestedIds: string[];
  before: StorefrontContext | null; after: StorefrontContext | null;
  products: { id: string; displayPrice: string | null; price: number | null; currency: string | null }[];
  result: "accepted" | "storefront_changed" | "currency_mismatch" | "failed" | "superseded";
};

/** Read fresh native metadata. expo-iap 5.5.1's hook keeps the first product
 * for each ID, even when a subsequent query returns a new storefront price. */
export class StoreCatalog<Product extends { id: string; displayPrice?: string; price?: number | null; currency?: string }> {
  state: StoreCatalogState<Product> = { items: [], loading: false, failed: false };
  diagnostics: PriceDiagnostic[] = [];
  failureReason: "unavailable" | "storefront_changed" | "currency_mismatch" | null = null;
  private generation = 0;
  private alive = true;
  private listeners = new Set<(state: StoreCatalogState<Product>) => void>();

  constructor(private readonly deps: {
    storefront(): Promise<StorefrontContext>;
    fetch(skus: string[]): Promise<Product[]>;
  }) {}

  subscribe(listener: (state: StoreCatalogState<Product>) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => { this.listeners.delete(listener); };
  }

  dispose(): void { this.alive = false; this.generation += 1; this.listeners.clear(); }

  invalidate(): void {
    this.generation += 1;
    this.failureReason = null;
    this.publish({ items: [], loading: false, failed: false });
  }

  private record(sample: PriceDiagnostic): void {
    if (!this.alive) return;
    this.diagnostics = [...this.diagnostics.slice(-19), sample];
  }

  private publish(state: StoreCatalogState<Product>): void {
    if (!this.alive) return;
    this.state = state;
    for (const listener of this.listeners) listener(state);
  }

  async refresh(skus: string[], reason = "focus"): Promise<Product[] | null> {
    if (!this.alive || !skus.length) return null;
    const generation = ++this.generation;
    this.failureReason = null;
    let failureReason: NonNullable<StoreCatalog<Product>["failureReason"]> = "unavailable";
    this.publish({ items: [], loading: true, failed: false });
    try {
      // A settings/store-account change during the query gets one fresh attempt.
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const before = await this.deps.storefront();
        const items = await this.deps.fetch(skus);
        const after = await this.deps.storefront();
        const sample: PriceDiagnostic = { loadedAt: Date.now(), reason, requestedIds: [...skus], before, after,
          products: items.map((item) => ({ id: item.id, displayPrice: item.displayPrice ?? null, price: item.price ?? null, currency: item.currency ?? null })), result: "accepted" };
        if (!this.alive || generation !== this.generation) { this.record({ ...sample, result: "superseded" }); return null; }
        if (before.id !== after.id || before.countryCode !== after.countryCode || before.currency !== after.currency) {
          failureReason = "storefront_changed";
          this.record({ ...sample, result: "storefront_changed" });
          continue;
        }
        // StoreKit can return USD products for a stable non-USD storefront in
        // TestFlight. Never publish or convert that quote. One refetch handles
        // delayed native metadata; persistent mismatch stays unpurchasable.
        if (after.currency && items.some((item) => item.currency !== after.currency)) {
          failureReason = "currency_mismatch";
          this.record({ ...sample, result: "currency_mismatch" });
          continue;
        }
        this.record(sample);
        const requested = new Set(skus);
        const fresh = [...new Map(items.filter((item) => requested.has(item.id)).map((item) => [item.id, item])).values()];
        this.publish({ items: fresh, loading: false, failed: false });
        return fresh;
      }
      throw new Error("storefront_changed");
    } catch {
      if (this.alive && generation === this.generation) {
        this.failureReason = failureReason;
        this.record({ loadedAt: Date.now(), reason, requestedIds: [...skus], before: null, after: null, products: [], result: "failed" });
        this.publish({ items: [], loading: false, failed: true });
      }
      return null;
    }
  }
}
