import type { StorefrontContext } from "./storefront";

export type StoreCatalogState<Product> = { items: Product[]; loading: boolean; failed: boolean };
export type PriceDiagnostic = {
  loadedAt: number; reason: string; requestedIds: string[];
  before: StorefrontContext | null; after: StorefrontContext | null;
  products: { id: string; displayPrice: string | null; price: number | null; currency: string | null }[];
  result: "accepted" | "storefront_changed" | "currency_mismatch" | "failed" | "timed_out" | "superseded";
};

/** Read fresh native metadata. expo-iap 5.5.1's hook keeps the first product
 * for each ID, even when a subsequent query returns a new storefront price. */
export class StoreCatalog<Product extends { id: string; displayPrice?: string; price?: number | null; currency?: string }> {
  state: StoreCatalogState<Product> = { items: [], loading: false, failed: false };
  diagnostics: PriceDiagnostic[] = [];
  failureReason: "unavailable" | "storefront_changed" | "currency_mismatch" | "timeout" | null = null;
  private generation = 0;
  private alive = true;
  private cancelPending: (() => void) | null = null;
  private listeners = new Set<(state: StoreCatalogState<Product>) => void>();

  constructor(private readonly deps: {
    storefront(): Promise<StorefrontContext>;
    fetch(skus: string[]): Promise<Product[]>;
    schedule?(run: () => void, delay: number): () => void;
  }) {}

  subscribe(listener: (state: StoreCatalogState<Product>) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => { this.listeners.delete(listener); };
  }

  dispose(): void {
    this.alive = false;
    this.generation += 1;
    this.cancelPending?.();
    this.cancelPending = null;
    this.listeners.clear();
  }

  invalidate(): void {
    this.generation += 1;
    this.cancelPending?.();
    this.cancelPending = null;
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
    this.cancelPending?.();
    this.failureReason = null;
    let failureReason: NonNullable<StoreCatalog<Product>["failureReason"]> = "unavailable";
    let before: StorefrontContext | null = null;
    let after: StorefrontContext | null = null;
    let products: PriceDiagnostic["products"] = [];
    const sample = (result: PriceDiagnostic["result"]): PriceDiagnostic => ({
      loadedAt: Date.now(), reason, requestedIds: [...skus], before, after, products, result,
    });
    const timedOut = new Error("price_query_timeout");
    let interrupt!: (error: Error) => void;
    const interrupted = new Promise<never>((_, reject) => { interrupt = reject; });
    const schedule = this.deps.schedule ?? ((run: () => void, delay: number) => {
      const timer = setTimeout(run, delay);
      return () => clearTimeout(timer);
    });
    // One deadline covers both attempts and every native read, including a
    // Storefront.current call that never resolves after an Apple account change.
    const cancelTimeout = schedule(() => interrupt(timedOut), 15_000);
    const cancelPending = () => { cancelTimeout(); interrupt(new Error("price_query_superseded")); };
    this.cancelPending = cancelPending;
    const read = <T>(query: Promise<T>): Promise<T> => Promise.race([query, interrupted]);
    this.publish({ items: [], loading: true, failed: false });
    try {
      // A settings/store-account change during the query gets one fresh attempt.
      for (let attempt = 0; attempt < 2; attempt += 1) {
        before = null; after = null; products = [];
        before = await read(this.deps.storefront());
        const items = await read(this.deps.fetch(skus));
        products = items.map((item) => ({ id: item.id, displayPrice: item.displayPrice ?? null, price: item.price ?? null, currency: item.currency ?? null }));
        after = await read(this.deps.storefront());
        if (!this.alive || generation !== this.generation) { this.record(sample("superseded")); return null; }
        if (before.id !== after.id || before.countryCode !== after.countryCode || before.currency !== after.currency) {
          failureReason = "storefront_changed";
          this.record(sample("storefront_changed"));
          continue;
        }
        // StoreKit can return USD products for a stable non-USD storefront in
        // TestFlight. Never publish or convert that quote. One refetch handles
        // delayed native metadata; persistent mismatch stays unpurchasable.
        if (after.currency && items.some((item) => item.currency !== after.currency)) {
          failureReason = "currency_mismatch";
          this.record(sample("currency_mismatch"));
          continue;
        }
        const requested = new Set(skus);
        const fresh = [...new Map(items.filter((item) => requested.has(item.id)).map((item) => [item.id, item])).values()];
        if (!fresh.length) throw new Error("no_store_products");
        this.record(sample("accepted"));
        this.publish({ items: fresh, loading: false, failed: false });
        return fresh;
      }
      throw new Error("storefront_changed");
    } catch (error) {
      if (this.alive && generation === this.generation) {
        this.failureReason = error === timedOut ? "timeout" : failureReason;
        this.record(sample(error === timedOut ? "timed_out" : "failed"));
        this.publish({ items: [], loading: false, failed: true });
      } else this.record(sample("superseded"));
      return null;
    } finally {
      cancelTimeout();
      if (this.cancelPending === cancelPending) this.cancelPending = null;
    }
  }
}
