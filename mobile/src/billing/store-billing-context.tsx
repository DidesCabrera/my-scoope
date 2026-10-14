import { ErrorCode, fetchProducts as fetchNativeProducts, finishTransaction, getAvailablePurchases, getPendingTransactionsIOS, getStorefront, syncIOS, type Product, type ProductOrSubscription, type ProductSubscription, type Purchase, useIAP } from "expo-iap";
import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { AppState, Platform } from "react-native";

import { useSession } from "@/auth/session-context";
import { PurchaseCoordinator, type BillingState } from "./purchase-coordinator";
import { restoreAccountPurchases } from "./restore-purchases";
import { StoreCatalog } from "./store-catalog";
import { storeBillingError } from "./store-errors";

type StoreBilling = {
  state: BillingState;
  coordinator: PurchaseCoordinator;
  store: ReturnType<typeof useIAP>;
  catalogBusy: boolean;
  catalogError: string | null;
  refreshCatalog(): Promise<ProductOrSubscription[] | null>;
  restore(): Promise<{ found: number; verified: number } | undefined>;
  buy(productId: string, basePlanId?: string, pack?: boolean): Promise<void>;
};
const Context = createContext<StoreBilling | null>(null);

export function StoreBillingProvider({ children }: PropsWithChildren) {
  const { status, session } = useSession();
  if (status !== "authenticated" || !session || Platform.OS === "web") return children;
  return <AccountStoreBilling key={session.user_id}>{children}</AccountStoreBilling>;
}

function AccountStoreBilling({ children }: PropsWithChildren) {
  const { apiRequest } = useSession();
  const provider = Platform.OS === "android" ? "google_play" : "apple_app_store";
  const coordinator = useMemo(() => new PurchaseCoordinator({
    provider, apiRequest, errorMessage: (error) => storeBillingError(error, "verify"),
    finish: (purchase, isConsumable) => finishTransaction({ purchase: purchase as Purchase, isConsumable }),
  }), [apiRequest, provider]);
  const [state, setState] = useState(coordinator.state);
  const catalog = useMemo(() => new StoreCatalog<ProductOrSubscription>({
    storefront: () => Platform.OS === "ios" ? getStorefront() : Promise.resolve("google_play"),
    fetch: async (skus) => await fetchNativeProducts({ skus, type: "all" }) ?? [],
  }), []);
  const [catalogState, setCatalogState] = useState(catalog.state);
  const [restoring, setRestoring] = useState(false);
  const [storeError, setStoreError] = useState<string | null>(null);
  const restoreLock = useRef(false);
  const store = useIAP({
    onPurchaseSuccess: (purchase) => { if (!restoreLock.current) void coordinator.submit(purchase, false, "event"); },
    onPurchaseError: (error) => {
      if (error.code === ErrorCode.DeferredPayment || error.code === ErrorCode.Pending) coordinator.awaitingApproval();
      else coordinator.storeFailed(error.code === ErrorCode.UserCancelled ? null : storeBillingError(error));
    },
    onError: (error) => {
      if ("code" in error && error.code === ErrorCode.UserCancelled) { coordinator.storeFailed(null); return; }
      setStoreError("No pudimos conectar con la tienda. Comprueba tu conexión y vuelve a abrir la app si el problema continúa.");
      coordinator.storeFailed(storeBillingError(error));
    },
  });

  useEffect(() => coordinator.subscribe(setState), [coordinator]);
  useEffect(() => () => coordinator.dispose(), [coordinator]);
  useEffect(() => catalog.subscribe(setCatalogState), [catalog]);
  useEffect(() => () => catalog.dispose(), [catalog]);
  const catalogIds = [...new Set([
    ...(state.overview?.products ?? []), ...(state.overview?.credit_packs ?? []),
  ].filter((product) => product.provider === provider).map((product) => product.product_id))].sort().join(",");
  const refreshCatalog = useCallback(() => catalog.refresh(catalogIds ? catalogIds.split(",") : []), [catalog, catalogIds]);
  const recoverPending = useCallback(async (retry = false) => {
    const pending = Platform.OS === "ios" ? await getPendingTransactionsIOS() : await getAvailablePurchases();
    for (const purchase of pending) await coordinator.submit(purchase, retry, "recovery");
  }, [coordinator]);
  useEffect(() => {
    let active = true;
    if (store.connected) {
      void recoverPending().then(() => { if (active) setStoreError(null); })
        .catch(() => { if (active) setStoreError("No pudimos consultar las transacciones pendientes. Puedes reintentarlo con Restaurar compras."); });
    }
    return () => { active = false; };
  }, [recoverPending, store.connected]);
  useEffect(() => {
    const listener = AppState.addEventListener("change", (next) => {
      if (next === "active" && store.connected) {
        void refreshCatalog();
        void recoverPending(true).catch(() => undefined);
        if (["pending", "activating"].includes(coordinator.state.phase)) void coordinator.refresh().catch(() => undefined);
      }
    });
    return () => listener.remove();
  }, [coordinator, recoverPending, refreshCatalog, store.connected]);

  const restore = async () => {
    if (restoreLock.current || coordinator.state.busy) return;
    restoreLock.current = true;
    coordinator.clearMessages();
    setStoreError(null);
    setRestoring(true);
    try {
      return await restoreAccountPurchases({
        synchronize: async () => {
          if (Platform.OS === "ios" && !await syncIOS()) throw new Error("Apple no completó la restauración. Inténtalo nuevamente.");
        },
        available: () => getAvailablePurchases({ alsoPublishToEventListenerIOS: false, onlyIncludeActiveItemsIOS: true }),
        pending: () => Platform.OS === "ios" ? getPendingTransactionsIOS() : Promise.resolve([]),
        submit: (purchase, retry) => coordinator.submit(purchase, retry, "restore"), refresh: () => coordinator.reconcile(),
      });
    } finally { restoreLock.current = false; setRestoring(false); void refreshCatalog(); }
  };
  const buy = async (productId: string, basePlanId = "", pack = false) => {
    coordinator.clearMessages();
    setStoreError(null);
    const fresh = await refreshCatalog();
    if (!fresh?.some((product) => product.id === productId)) {
      setStoreError("No pudimos actualizar el precio de la tienda. Reintenta consultar los precios antes de comprar.");
      return;
    }
    setStoreError(null);
    if (!coordinator.begin(productId)) return;
    const overview = coordinator.state.overview!;
    try {
      let result: Awaited<ReturnType<typeof store.requestPurchase>>;
      if (Platform.OS === "android") {
        const product = fresh.find((item) => item.id === productId) as ProductSubscription | undefined;
        const offer = product?.subscriptionOffers?.find((item) => item.basePlanIdAndroid === basePlanId && item.offerTokenAndroid);
        if (!pack && !offer?.offerTokenAndroid) throw new Error("El plan no está disponible en Google Play.");
        result = await store.requestPurchase({ type: pack ? "in-app" : "subs", request: { google: {
          skus: [productId], obfuscatedAccountId: overview.google_obfuscated_account_id,
          ...(!pack ? { subscriptionOffers: [{ sku: productId, offerToken: offer!.offerTokenAndroid! }] } : {}),
        } } });
      } else {
        result = await store.requestPurchase({ type: pack ? "in-app" : "subs", request: { apple: {
          sku: productId, appAccountToken: overview.app_account_token, andDangerouslyFinishTransactionAutomatically: false,
        } } });
      }
      // The promise and native callback may both deliver the same receipt.
      // The coordinator shares the task instead of submitting twice.
      for (const purchase of Array.isArray(result) ? result : result ? [result] : []) await coordinator.submit(purchase, false, "purchase");
      if (coordinator.state.phase === "store") {
        try { await coordinator.reconcile(true); } catch { /* Keep store approval pending when its status cannot be read. */ }
        coordinator.awaitingApproval();
      }
    } catch (error) {
      const code = error && typeof error === "object" && "code" in error ? error.code : null;
      if (code === ErrorCode.UserCancelled) { coordinator.storeFailed(null); return; }
      try {
        const recovered = Platform.OS === "ios" ? await getPendingTransactionsIOS() : await getAvailablePurchases();
        const matching = recovered.filter((purchase) => purchase.productId === productId);
        if (matching.length) {
          for (const purchase of matching) await coordinator.submit(purchase, true, "recovery");
          return;
        }
      } catch { /* Retain the original error, without claiming that no charge occurred. */ }
      coordinator.storeFailed("No pudimos confirmar el resultado con la tienda. Revisa tu suscripción o usa Restaurar compras antes de volver a comprar.");
    } finally { void refreshCatalog(); }
  };
  return <Context.Provider value={{
    state: { ...state, error: state.error ?? storeError, busy: state.busy || restoring }, coordinator,
    store: { ...store, products: catalogState.items.filter((item) => item.type === "in-app") as Product[],
      subscriptions: catalogState.items.filter((item) => item.type === "subs") as ProductSubscription[] },
    catalogBusy: catalogState.loading,
    catalogError: catalogState.failed ? "No pudimos consultar los precios actuales de la tienda. Inténtalo nuevamente." : null,
    refreshCatalog, restore, buy,
  }}>{children}</Context.Provider>;
}

export function useStoreBilling(): StoreBilling | null { return useContext(Context); }
