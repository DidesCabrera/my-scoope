import type { StorePurchase } from "./purchase-coordinator";

type RestoreDependencies = {
  synchronize(): Promise<void>;
  available(): Promise<StorePurchase[]>;
  pending(): Promise<StorePurchase[]>;
  submit(purchase: StorePurchase, retry: boolean): Promise<boolean>;
  refresh(): Promise<void>;
};

export async function restoreAccountPurchases(deps: RestoreDependencies): Promise<{ found: number; verified: number }> {
  await deps.synchronize();
  const available = await deps.available();
  const pending = await deps.pending();
  const unique = new Map([...pending, ...available].filter((item) => item.id || item.purchaseToken)
    .map((purchase) => [purchase.id || purchase.purchaseToken, purchase]));
  let verified = 0;
  for (const purchase of unique.values()) if (await deps.submit(purchase, true)) verified += 1;
  await deps.refresh();
  return { found: unique.size, verified };
}
