import type { SubscriptionData } from "@/api/types";

type StoreSubscription = {
  isActive: boolean;
  productId: string;
  basePlanIdAndroid?: string | null;
  purchaseTokenAndroid?: string | null;
};

export function googlePlayReplacement(
  overview: SubscriptionData,
  active: StoreSubscription[],
  productId: string,
  basePlanId: string,
) {
  const currentPlans = overview.evidence.filter(
    (item) => item.provider === "google_play" && item.status === "authorized",
  );
  if (currentPlans.length > 1) {
    throw new Error("Hay más de una suscripción de Google Play activa. Contacta a soporte antes de cambiar de plan.");
  }
  const configured = overview.products.filter((item) => item.provider === "google_play");
  const storePlans = active.filter(
    (item) => item.isActive && configured.some((product) => product.product_id === item.productId),
  );
  if (storePlans.length > 1) {
    throw new Error("Google Play muestra más de una suscripción activa. Contacta a soporte antes de comprar.");
  }
  const current = currentPlans[0];
  if (!current) {
    if (storePlans.length) {
      throw new Error("Google Play muestra una suscripción de otra cuenta. Inicia sesión en My Scoope con esa cuenta antes de comprar.");
    }
    return null;
  }
  const oldPurchase = storePlans.find(
    (item) => item.productId === current.product_id && item.purchaseTokenAndroid,
  );
  if (!oldPurchase?.purchaseTokenAndroid) {
    throw new Error("No encontramos tu suscripción actual en Google Play. Restaura las compras con la misma cuenta de Play antes de cambiar de plan.");
  }
  if (oldPurchase.productId === productId && oldPurchase.basePlanIdAndroid === basePlanId) {
    throw new Error("Ya tienes activo este plan de Google Play.");
  }
  const oldPlan = configured.find((item) => item.product_id === oldPurchase.productId)?.plan_name.toLowerCase();
  const newPlan = configured.find((item) => item.product_id === productId)?.plan_name.toLowerCase();
  return {
    purchaseToken: oldPurchase.purchaseTokenAndroid,
    subscriptionProductReplacementParams: {
      oldProductId: oldPurchase.productId,
      replacementMode: oldPlan === "pro" && newPlan === "basic" ? "deferred" as const : "charge-full-price" as const,
    },
  };
}
