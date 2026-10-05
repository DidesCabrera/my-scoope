import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import {
  ErrorCode,
  finishTransaction,
  getAvailablePurchases,
  type Purchase,
  useIAP,
} from "expo-iap";
import { useCallback, useEffect, useRef, useState } from "react";
import { Info, RefreshCcw, Sparkles, WalletCards } from "lucide-react-native";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData, SubscriptionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Card, InlineNotice, LoadingState, Screen, SectionDivider, SectionHeading, SectionTitle, textStyles } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { commercialPlanBenefits, SubscriptionPlanCard, SubscriptionPurchaseButton } from "@/components/subscriptions/subscription-plan-card";
import { tokens } from "@/design/tokens";
import { subscriptionPlanAccent } from "@/presentation/subscription";

function purchaseErrorCode(error: unknown): string {
  if (!error || typeof error !== "object" || !("code" in error)) return "";
  return String(error.code ?? "").trim().toLowerCase();
}

export default function SubscriptionScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [overview, setOverview] = useState<SubscriptionData | null>(null);
  const [entitlements, setEntitlements] = useState<EntitlementsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoreNotice, setRestoreNotice] = useState<string | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const handledTransactions = useRef(new Set<string>());
  const restoring = useRef(false);

  const submitPurchase = useCallback(async (purchase: Purchase): Promise<boolean> => {
    const key = purchase.id || purchase.purchaseToken || "";
    if (!purchase.purchaseToken || !key || handledTransactions.current.has(key)) return false;
    handledTransactions.current.add(key);
    setWorking(true);
    setError(null);
    try {
      const isGooglePlay = Platform.OS === "android";
      const isCreditPack = overview?.credit_packs.some((pack) => pack.product_id === purchase.productId) ?? false;
      await apiRequest(isCreditPack
        ? isGooglePlay ? "/api/v1/credit-packs/google-play/purchases" : "/api/v1/credit-packs/apple/transactions"
        : isGooglePlay ? "/api/v1/subscriptions/google-play/purchases" : "/api/v1/subscriptions/apple/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isGooglePlay
          ? { purchase_token: purchase.purchaseToken }
          : { signed_transaction: purchase.purchaseToken }),
      });
      await finishTransaction({ purchase, isConsumable: isCreditPack });
      const [nextOverview, nextEntitlements] = await Promise.all([
        apiRequest<SubscriptionData>("/api/v1/subscriptions"),
        apiRequest<EntitlementsData>("/api/v1/entitlements"),
      ]);
      setOverview(nextOverview);
      setEntitlements(nextEntitlements);
      return true;
    } catch (nextError) {
      // A failed verification remains pending at the store. Do not replay it
      // continuously when the purchase list or component state refreshes.
      // The user can explicitly retry it with Restore purchases.
      setError(userFacingError(nextError));
      return false;
    } finally {
      setWorking(false);
    }
  }, [apiRequest, overview]);

  const {
    connected,
    products,
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
      const [nextOverview, nextEntitlements] = await Promise.all([
        apiRequest<SubscriptionData>("/api/v1/subscriptions"),
        apiRequest<EntitlementsData>("/api/v1/entitlements"),
      ]);
      setOverview(nextOverview);
      setEntitlements(nextEntitlements);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  const openActions = useCallback(() => setActionsVisible(true), []);
  const closeActions = useCallback(() => setActionsVisible(false), []);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "more", label: "Acciones de suscripciones y bolsas", onPress: openActions }, fallback: "/account", identityVisible: compactHeaderVisible, mode: "back", title: "Suscripciones y Bolsas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, openActions, setHeaderPresentation]));
  useFocusEffect(useCallback(() => { void load(); }, [load]));

  useEffect(() => {
    const provider = Platform.OS === "android" ? "google_play" : "apple_app_store";
    const ids = [...new Set(overview?.products.filter((item) => item.provider === provider).map((item) => item.product_id) ?? [])];
    if ((Platform.OS === "ios" || Platform.OS === "android") && connected && ids.length > 0) {
      void fetchProducts({ skus: ids, type: "subs" }).catch((nextError) => setError(userFacingError(nextError)));
    }
  }, [connected, fetchProducts, overview?.products]);

  useEffect(() => {
    const provider = Platform.OS === "android" ? "google_play" : "apple_app_store";
    const ids = [...new Set(overview?.credit_packs.filter((item) => item.provider === provider).map((item) => item.product_id) ?? [])];
    if ((Platform.OS === "ios" || Platform.OS === "android") && connected && ids.length > 0) {
      void fetchProducts({ skus: ids, type: "in-app" }).catch((nextError) => setError(userFacingError(nextError)));
    }
  }, [connected, fetchProducts, overview?.credit_packs]);

  useEffect(() => {
    const pending = setTimeout(() => {
      if (!restoring.current) {
        for (const purchase of availablePurchases) void submitPurchase(purchase);
      }
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

  const buyCreditPack = async (productId: string) => {
    if (!overview?.credit_packs.some((pack) => pack.product_id === productId)) return;
    setWorking(true);
    setError(null);
    try {
      if (Platform.OS === "android") {
        await requestPurchase({
          request: { google: { skus: [productId], obfuscatedAccountId: overview.google_obfuscated_account_id } },
          type: "in-app",
        });
      } else {
        await requestPurchase({
          request: { apple: {
            sku: productId,
            appAccountToken: overview.app_account_token,
            andDangerouslyFinishTransactionAutomatically: false,
          } },
          type: "in-app",
        });
      }
    } catch (nextError) {
      if (purchaseErrorCode(nextError) === ErrorCode.AlreadyOwned) {
        try {
          const recovered = await getAvailablePurchases();
          const matching = recovered.filter((purchase) => purchase.productId === productId);
          if (matching.length > 0) {
            for (const purchase of matching) {
              handledTransactions.current.delete(purchase.id || purchase.purchaseToken || "");
              await submitPurchase(purchase);
            }
            return;
          }
        } catch {
          // Keep the store error below if the pending purchase cannot be read.
        }
      }
      setWorking(false);
      if (purchaseErrorCode(nextError) !== ErrorCode.UserCancelled) setError(userFacingError(nextError));
    }
  };

  const restore = async () => {
    if (restoring.current) return;
    restoring.current = true;
    setWorking(true);
    setError(null);
    setRestoreNotice(null);
    try {
      handledTransactions.current.clear();
      await restorePurchases();
      const recovered = await getAvailablePurchases();
      let restored = 0;
      for (const purchase of recovered) {
        if (await submitPurchase(purchase)) restored += 1;
      }
      if (recovered.length === 0) {
        setRestoreNotice("No hay compras pendientes de restaurar. Las bolsas ya acreditadas permanecen en tu saldo.");
      } else if (restored === recovered.length) {
        setRestoreNotice("Revisamos tus compras disponibles. Comprueba tu plan y saldo actualizados.");
      } else {
        setError("No pudimos verificar todas las compras disponibles. Inténtalo nuevamente más tarde.");
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      restoring.current = false;
      setWorking(false);
    }
  };

  const storeProvider = Platform.OS === "android" ? "google_play" : "apple_app_store";
  const subscriptionPlans = ["Basic", "Pro"].map((planName) => ({
    planName,
    products: (overview?.products ?? [])
      .filter((item) => item.provider === storeProvider && item.plan_name.trim().toLowerCase() === planName.toLowerCase())
      .sort((left, right) => (left.interval === "month" ? 0 : 1) - (right.interval === "month" ? 0 : 1)),
  })).filter((plan) => plan.products.length > 0);

  return (
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      <AppHeader eyebrow="Cuenta" title="Suscripciones y Bolsas" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {restoreNotice ? <InlineNotice>{restoreNotice}</InlineNotice> : null}
      {overview?.duplicate_active_providers ? (
        <InlineNotice tone="warning">Detectamos más de un canal de cobro activo. El equipo puede revisarlo sin interrumpir tu acceso.</InlineNotice>
      ) : null}
      <Card accent={subscriptionPlanAccent(entitlements?.plan_name ?? overview?.plan_name)}>
        <View style={styles.subscriptionHeading}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>SUSCRIPCIÓN ACTUAL</Text>
            <Text style={styles.planName}>{entitlements?.plan_name ?? overview?.plan_name ?? "Consultando…"}</Text>
          </View>
        </View>
        {entitlements ? <AssistantCreditBalance availability={entitlements} contained /> : null}
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
          <SectionTitle title="Suscripciones disponibles" titleStyle={styles.commercialSectionTitle} />
          <SubscriptionPlanCard accent={tokens.color.fat} benefits={commercialPlanBenefits.Free} caption="Incluido sin costo." name="Free" price="$0/mes" />
          {subscriptionPlans.map((plan) => {
            const monthlyProduct = plan.products.find((item) => item.interval === "month");
            const monthlyStoreProduct = subscriptions.find((item) => item.id === monthlyProduct?.product_id);
            const monthlyAndroidOffer = monthlyStoreProduct?.subscriptionOffers?.find(
              (item) => item.basePlanIdAndroid === monthlyProduct?.base_plan_id,
            );
            const monthlyDisplayPrice = Platform.OS === "android" ? monthlyAndroidOffer?.displayPrice : monthlyStoreProduct?.displayPrice;
            const monthlyNumericPrice = Platform.OS === "android" ? monthlyAndroidOffer?.price : monthlyStoreProduct?.price;
            return (
            <SubscriptionPlanCard accent={subscriptionPlanAccent(plan.planName) ?? tokens.color.contextual} benefits={commercialPlanBenefits[plan.planName as "Basic" | "Pro"] ?? []} key={plan.planName} name={plan.planName} price={monthlyDisplayPrice ? `${monthlyDisplayPrice}/mes` : "Consultando…"}>
              <Text style={textStyles.caption}>Elige la modalidad de tu suscripción.</Text>
              {plan.products.map((configured) => {
                  const storeProduct = subscriptions.find((item) => item.id === configured.product_id);
                  const androidOffer = storeProduct?.subscriptionOffers?.find(
                    (item) => item.basePlanIdAndroid === configured.base_plan_id,
                  );
                  const androidUnavailable = storeProduct && "productStatusAndroid" in storeProduct
                    && storeProduct.productStatusAndroid === "not-found";
                  const price = Platform.OS === "android"
                    ? androidOffer?.displayPrice ?? (androidUnavailable ? "No disponible" : "Consultando…")
                    : storeProduct?.displayPrice ?? "Consultando…";
                  const numericPrice = Platform.OS === "android" ? androidOffer?.price : storeProduct?.price;
                  const interval = configured.interval === "year" ? "Anual" : "Mensual";
                  const annualDiscount = configured.interval === "year" && monthlyNumericPrice && numericPrice
                    ? Math.max(0, Math.round((1 - (numericPrice / (monthlyNumericPrice * 12))) * 100))
                    : 0;
                  const priceExplanation = configured.interval === "year"
                    ? `${price}/año${annualDiscount > 0 ? ` · Ahorra ${annualDiscount}%` : ""}`
                    : `${price}/mes`;
                  return (
                    <SubscriptionPurchaseButton
                      disabled={!connected || !storeProduct || (Platform.OS === "android" && !androidOffer)}
                      key={configured.product_id}
                      label={`${interval} · ${priceExplanation}`}
                      loading={working}
                      onPress={() => void buy(configured.product_id, configured.base_plan_id)}
                    />
                  );
                })}
            </SubscriptionPlanCard>
            );
          })}
        </>
      ) : null}

      {overview?.can_buy_credit_packs && overview.credit_packs.length ? (
        <>
          <SectionDivider />
          <SectionHeading
            icon={<Sparkles color={tokens.color.entityIconForeground} size={18} />}
            title="Bolsas de créditos"
            titleStyle={styles.commercialSectionTitle}
          />
          <Text style={textStyles.muted}>Compra disponible en Basic y Pro.</Text>
          {overview.credit_packs.filter((item) => item.provider === (Platform.OS === "android" ? "google_play" : "apple_app_store")).map((configured) => {
            const storeProduct = products.find((item) => item.id === configured.product_id);
            return (
              <Card accent={tokens.color.carbs} key={configured.product_id}>
                <View style={styles.row}>
                  <View style={styles.copy}>
                    <Text style={styles.eyebrow}>BOLSA DE CRÉDITOS</Text>
                    <Text style={styles.productName}>{configured.credits.toLocaleString("es-CL")} créditos</Text>
                    <Text style={textStyles.caption}>Permanecen en tu cuenta si cambias de plan.</Text>
                  </View>
                  <CreditPackPriceChip label={storeProduct?.displayPrice ?? "Consultando…"} />
                </View>
                <SubscriptionPurchaseButton
                  disabled={!connected || !storeProduct}
                  label={`Comprar ${configured.credits.toLocaleString("es-CL")} créditos`}
                  loading={working}
                  onPress={() => void buyCreditPack(configured.product_id)}
                />
              </Card>
            );
          })}
        </>
      ) : null}

      <ActionSheetModal onRequestClose={closeActions} visible={actionsVisible}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
          <ActionSheetHeader icon={WalletCards} onClose={closeActions} title="Suscripciones y Bolsas" />
          <View style={styles.sheetContent}>
            <ActionSheetActions>
              <ActionSheetAction icon={Info} label="Ver detalles de Suscripciones y Bolsas" onPress={() => { closeActions(); router.push("/subscription-details" as Href); }} />
              <Pressable accessibilityRole="button" accessibilityState={{ busy: working, disabled: working }} disabled={working} onPress={() => { closeActions(); void restore(); }} style={({ pressed }) => [styles.actionRow, working && styles.disabledAction, pressed && styles.pressed]}>
                <RefreshCcw color={tokens.color.textMain} size={18} />
                <Text style={styles.actionLabel}>Restaurar compras</Text>
              </Pressable>
            </ActionSheetActions>
          </View>
        </SafeAreaView>
      </ActionSheetModal>
    </Screen>
  );
}

function CreditPackPriceChip({ label }: { label: string }) {
  return (
    <View style={[styles.planPriceChip, styles.creditPackPriceChip]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="credit-pack-price-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#credit-pack-price-macros)" height="100%" width="100%" />
      </Svg>
      <Text numberOfLines={1} style={styles.planPriceChipLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 15, fontWeight: tokens.weight.medium },
  actionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingVertical: tokens.spacing.sm },
  closeButton: { alignItems: "center", height: 40, justifyContent: "center", width: 40 },
  commercialSectionTitle: { fontSize: tokens.type.section, lineHeight: 26 },
  creditPackPriceChip: { overflow: "hidden" },
  row: { alignItems: "center", flexDirection: "row", gap: 16, justifyContent: "space-between" },
  copy: { flex: 1, gap: 4 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  disabledAction: { opacity: 0.45 },
  planPriceChip: { alignItems: "center", borderRadius: tokens.radius.pill, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.xs },
  planPriceChipLabel: { color: tokens.color.surfaceApp, fontSize: 16, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  planName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  productName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  pressed: { opacity: 0.65 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, overflow: "hidden" },
  subscriptionHeading: { alignItems: "center", flexDirection: "row" },
});
