export type StoreCatalogState<Product> = { items: Product[]; loading: boolean; failed: boolean };

/** Read fresh native metadata. expo-iap 5.5.1's hook keeps the first product
 * for each ID, even when a subsequent query returns a new storefront price. */
export class StoreCatalog<Product extends { id: string }> {
  state: StoreCatalogState<Product> = { items: [], loading: false, failed: false };
  private generation = 0;
  private alive = true;
  private listeners = new Set<(state: StoreCatalogState<Product>) => void>();

  constructor(private readonly deps: {
    storefront(): Promise<string>;
    fetch(skus: string[]): Promise<Product[]>;
  }) {}

  subscribe(listener: (state: StoreCatalogState<Product>) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => { this.listeners.delete(listener); };
  }

  dispose(): void { this.alive = false; this.generation += 1; this.listeners.clear(); }

  private publish(state: StoreCatalogState<Product>): void {
    if (!this.alive) return;
    this.state = state;
    for (const listener of this.listeners) listener(state);
  }

  async refresh(skus: string[]): Promise<Product[] | null> {
    if (!this.alive || !skus.length) return null;
    const generation = ++this.generation;
    this.publish({ items: [], loading: true, failed: false });
    try {
      // A settings/store-account change during the query gets one fresh attempt.
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const before = await this.deps.storefront();
        const items = await this.deps.fetch(skus);
        const after = await this.deps.storefront();
        if (!this.alive || generation !== this.generation) return null;
        if (before !== after) continue;
        const requested = new Set(skus);
        const fresh = [...new Map(items.filter((item) => requested.has(item.id)).map((item) => [item.id, item])).values()];
        this.publish({ items: fresh, loading: false, failed: false });
        return fresh;
      }
      throw new Error("storefront_changed");
    } catch {
      if (this.alive && generation === this.generation) this.publish({ items: [], loading: false, failed: true });
      return null;
    }
  }
}
