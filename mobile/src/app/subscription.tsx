import { Redirect, useFocusEffect, useRouter } from "expo-router";
import {
  deepLinkToSubscriptions,
  ErrorCode,
  finishTransaction,
  getAvailablePurchases,
  type Purchase,
  useIAP,
} from "expo-iap";
import { useCallback, useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SubscriptionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

const providerLabels: Record<string, string> = {
  apple_app_store: "App Store",
  google_play: "Google Play",
  paddle: "Paddle",
};

function purchaseErrorCode(error: unknown): string {
  if (!error || typeof error !== "object" || !("code" in error)) return "";
  return String(error.code ?? "").trim().toLowerCase();
}

export default function SubscriptionScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [overview, setOverview] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handledTransactions = useRef(new Set<string>());

  const submitPurchase = useCallback(async (purchase: Purchase) => {
    const key = purchase.id || purchase.purchaseToken || "";
    if (!purchase.purchaseToken || !key || handledTransactions.current.has(key)) return;
    handledTransactions.current.add(key);
    setWorking(true);
    setError(null);
    try {
      const isGooglePlay = Platform.OS === "android";
      const next = await apiRequest<SubscriptionData>(isGooglePlay
        ? "/api/v1/subscriptions/google-play/purchases"
        : "/api/v1/subscriptions/apple/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isGooglePlay
          ? { purchase_token: purchase.purchaseToken }
          : { signed_transaction: purchase.purchaseToken }),
      });
      await finishTransaction({ purchase, isConsumable: false });
      setOverview(next);
    } catch (nextError) {
      handledTransactions.current.delete(key);
      setError(userFacingError(nextError));
    } finally {
      setWorking(false);
    }
  }, [apiRequest]);

  const {
    connected,
    subscriptions,
    availablePurchases,
    fetchProducts,
    requestPurchase,
    restorePurchases,
  } = useIAP({
    onPurchaseSuccess: (purchase) => void submitPurchase(purchase),
    onPurchaseError: (purchaseError) => { setError(purchaseError.message); setWorking(false); },
    onError: (nextError) => { setError(nextError.message); setWorking(false); },
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOverview(await apiRequest<SubscriptionData>("/api/v1/subscriptions"));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  useEffect(() => {
    const provider = Platform.OS === "android" ? "google_play" : "apple_app_store";
    const ids = [...new Set(overview?.products.filter((item) => item.provider === provider).map((item) => item.product_id) ?? [])];
    if ((Platform.OS === "ios" || Platform.OS === "android") && connected && ids.length > 0) {
      void fetchProducts({ skus: ids, type: "subs" }).catch((nextError) => setError(userFacingError(nextError)));
    }
  }, [connected, fetchProducts, overview?.products]);

  useEffect(() => {
    const pending = setTimeout(() => {
      for (const purchase of availablePurchases) void submitPurchase(purchase);
    }, 0);
    return () => clearTimeout(pending);
  }, [availablePurchases, submitPurchase]);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Revisando tu suscripción…" />;

  const buy = async (productId: string, basePlanId = "") => {
    if (!overview) return;
    setWorking(true);
    setError(null);
    try {
      const storeProduct = subscriptions.find((item) => item.id === productId);
      if (Platform.OS === "android") {
        const offer = storeProduct?.subscriptionOffers?.find(
          (item) => item.basePlanIdAndroid === basePlanId && item.offerTokenAndroid,
        );
        if (!offer?.offerTokenAndroid) throw new Error("El plan seleccionado no está disponible en Google Play.");
        await requestPurchase({
          request: { google: {
            skus: [productId],
            subscriptionOffers: [{ sku: productId, offerToken: offer.offerTokenAndroid }],
            obfuscatedAccountId: overview.google_obfuscated_account_id,
          } },
          type: "subs",
        });
      } else {
        await requestPurchase({ request: { apple: {
            sku: productId,
            appAccountToken: overview.app_account_token,
            andDangerouslyFinishTransactionAutomatically: false,
        } }, type: "subs" });
      }
    } catch (nextError) {
      if (purchaseErrorCode(nextError) === ErrorCode.UserCancelled) {
        setError(null);
        setWorking(false);
        return;
      }

      try {
        const recovered = await getAvailablePurchases({
          alsoPublishToEventListenerIOS: false,
          onlyIncludeActiveItemsIOS: true,
        });
        const matching = recovered.filter((purchase) => purchase.productId === productId);
        if (matching.length > 0) {
          for (const purchase of matching) await submitPurchase(purchase);
          return;
        }
      } catch {
        // Preserve the original StoreKit failure below. A manual restore remains available.
      }

      setError(`${Platform.OS === "android" ? "Google Play" : "Apple"} no completó la compra. No se realizó ningún cobro; inténtalo nuevamente o usa Restaurar compras.`);
      setWorking(false);
    }
  };

  const restore = async () => {
    setWorking(true);
    setError(null);
    try {
      await restorePurchases();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setWorking(false);
    }
  };

  const manage = async () => {
    try {
      await deepLinkToSubscriptions();
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  };

  return (
    <Screen>
      <AppHeader eyebrow="Cuenta" title="Mi suscripción" />
      <Button label="Volver a hoy" onPress={() => router.back()} variant="secondary" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {overview?.duplicate_active_providers ? (
        <InlineNotice tone="warning">Detectamos más de un canal de cobro activo. El equipo puede revisarlo sin interrumpir tu acceso.</InlineNotice>
      ) : null}
      <Card accent={tokens.color.interactivePrimary}>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.plan}>{overview?.plan_name ?? "Sin plan"}</Text>
            <Text style={textStyles.caption}>Estado actual: {overview?.status ?? "—"}</Text>
          </View>
          <Pill label={overview?.status === "active" ? "Activo" : overview?.status ?? "—"} />
        </View>
      </Card>

      <Card muted>
        <SectionTitle title="Tu canal de compra" />
        <Text style={textStyles.muted}>Tu acceso funciona con la misma cuenta en todas las plataformas. Las cancelaciones y reembolsos se administran en el canal donde realizaste la compra.</Text>
      </Card>

      {!overview?.eligible ? (
        <Card muted>
          <SectionTitle title="Suscripción de consumidor" />
          <Text style={textStyles.muted}>Las compras dentro de la app están enfocadas en cuentas personales de seguimiento físico.</Text>
        </Card>
      ) : null}

      {overview?.eligible && !overview.purchases_enabled ? (
        <Card muted>
          <SectionTitle title="Compras próximamente" />
          <Text style={textStyles.muted}>Aún no hay productos de la tienda habilitados para comprar. Tu plan actual sigue funcionando normalmente.</Text>
        </Card>
      ) : null}

      {overview?.purchases_enabled && (Platform.OS === "ios" || Platform.OS === "android") ? (
        <>
          <SectionTitle detail="Precio oficial de App Store" title="Planes disponibles" />
          {overview.products.filter((item) => item.provider === (Platform.OS === "android" ? "google_play" : "apple_app_store")).map((configured) => {
            const storeProduct = subscriptions.find((item) => item.id === configured.product_id);
            const androidOffer = storeProduct?.subscriptionOffers?.find(
              (item) => item.basePlanIdAndroid === configured.base_plan_id,
            );
            return (
              <Card key={configured.product_id} muted>
                <View style={styles.row}>
                  <View style={styles.copy}>
                    <Text style={styles.productName}>{configured.plan_name}</Text>
                    <Text style={textStyles.caption}>{configured.interval === "year" ? "Anual" : "Mensual"}</Text>
                  </View>
                  <Text style={styles.price}>{Platform.OS === "android" ? androidOffer?.displayPrice ?? "Consultando…" : storeProduct?.displayPrice ?? "Consultando…"}</Text>
                </View>
                <Button
                  disabled={!connected || !storeProduct || (Platform.OS === "android" && !androidOffer)}
                  label={`Suscribirme a ${configured.plan_name}`}
                  loading={working}
                  onPress={() => void buy(configured.product_id, configured.base_plan_id)}
                />
              </Card>
            );
          })}
          <Button
            label="Restaurar compras"
            loading={working}
            onPress={() => void restore()}
            variant="secondary"
          />
        </>
      ) : null}

      {overview?.evidence.length ? (
        <Card muted>
          <SectionTitle title="Canales reconocidos" />
          {overview.evidence.map((item, index) => (
            <View key={`${item.provider}-${index}`} style={styles.row}>
              <Text style={textStyles.body}>{providerLabels[item.provider] ?? "Proveedor de pago"}</Text>
              <Text style={textStyles.caption}>{item.status}</Text>
            </View>
          ))}
          {Platform.OS === "ios" && overview.evidence.some((item) => item.provider === "apple_app_store") ? (
            <Button label="Gestionar en App Store" onPress={() => void manage()} variant="secondary" />
          ) : null}
        </Card>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", flexDirection: "row", gap: 16, justifyContent: "space-between" },
  copy: { flex: 1, gap: 4 },
  plan: { color: tokens.color.textMain, fontSize: 26, fontWeight: "900" },
  productName: { color: tokens.color.textMain, fontSize: 18, fontWeight: "800" },
  price: { color: tokens.color.textMain, fontSize: 17, fontWeight: "900" },
});
