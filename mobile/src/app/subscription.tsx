import { type Href, Redirect, Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import * as Clipboard from "expo-clipboard";
import { useCallback, useEffect, useRef, useState } from "react";
import { Info, RefreshCcw, Sparkles, WalletCards } from "lucide-react-native";
import { Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData, SubscriptionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useStoreBilling } from "@/billing/store-billing-context";
import { storeBillingError } from "@/billing/store-errors";
import { CreditDashboardGrid } from "@/components/assistant/credit-dashboard-grid";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Button, Card, InlineNotice, LoadingState, MyScoopeBrandLogo, Screen, SectionDivider, SectionHeading, SectionTitle, textStyles } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { commercialPlanBenefits, SubscriptionPlanCard, SubscriptionPurchaseButton } from "@/components/subscriptions/subscription-plan-card";
import { tokens } from "@/design/tokens";
import { appConfig } from "@/config/app-config";
import { internalHref } from "@/navigation/internal-href";
import { subscriptionPlanAccent } from "@/presentation/subscription";

export default function SubscriptionScreen() {
  const { origin, returnTo } = useLocalSearchParams<{ origin?: string; returnTo?: string }>();
  const isOnboarding = origin === "onboarding";
  const returnHref = internalHref(returnTo);
  const router = useRouter();
  const { status, apiRequest, refreshProfile } = useSession();
  const billing = useStoreBilling();
  const setHeaderPresentation = useHeaderPresentation();
  const [fallbackOverview, setFallbackOverview] = useState<SubscriptionData | null>(null);
  const [fallbackEntitlements, setFallbackEntitlements] = useState<EntitlementsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [localWorking, setLocalWorking] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [restoreNotice, setRestoreNotice] = useState<string | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [pricesVisible, setPricesVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const onboardingFinishing = useRef(false);
  const noticeGeneration = useRef(0);
  const screenFocused = useRef(false);
  const coordinator = billing?.coordinator;
  const overview = billing?.state.overview ?? fallbackOverview;
  const entitlements = billing?.state.entitlements ?? fallbackEntitlements;
  const working = localWorking || Boolean(billing?.state.busy);
  const error = localError ?? (restoreNotice ? null : billing?.state.error ?? billing?.catalogError);
  const activatingPlan = !restoreNotice && billing && ["verifying", "activating", "pending"].includes(billing.state.phase) ? billing.state.planName : null;
  const purchaseNotice = error || restoreNotice ? null : billing?.state.message
    ?? (activatingPlan ? "Estamos verificando los beneficios de tu compra. Puedes reintentar la verificación o restaurar tus compras." : null);
  const creditBlocked = entitlements?.credit_status === "frozen" || entitlements?.credit_status === "pending_reservation";
  const purchaseBlocked = working || Boolean(billing?.catalogBusy) || creditBlocked || Boolean(billing && ["pending", "activating"].includes(billing.state.phase));
  const connected = billing?.store.connected ?? false;
  const products = billing?.store.products ?? [];
  const subscriptions = billing?.store.subscriptions ?? [];
  const refreshCatalog = billing?.refreshCatalog;

  const finishOnboarding = useCallback(async () => {
    if (onboardingFinishing.current) return;
    onboardingFinishing.current = true;
    try {
      await apiRequest("/api/v1/onboarding/complete", { method: "POST" });
      await refreshProfile();
      router.replace(returnHref ?? ("/today" as Href));
    } finally { onboardingFinishing.current = false; }
  }, [apiRequest, refreshProfile, returnHref, router]);

  const load = useCallback(async () => {
    if (status !== "authenticated") return;
    setLoading(true);
    try {
      if (coordinator) await coordinator.refresh();
      else {
        const [nextOverview, nextEntitlements] = await Promise.all([
          apiRequest<SubscriptionData>("/api/v1/subscriptions", { cache: "no-store" }),
          apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" }),
        ]);
        setFallbackOverview(nextOverview);
        setFallbackEntitlements(nextEntitlements);
      }
      setLocalError(null);
    } catch (nextError) { if (!coordinator) setLocalError(userFacingError(nextError)); }
    finally { setLoading(false); }
  }, [apiRequest, coordinator, status]);
  const openActions = useCallback(() => setActionsVisible(true), []);
  const closeActions = useCallback(() => { setActionsVisible(false); setPricesVisible(false); }, []);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation(isOnboarding
      ? { action: { icon: "more", label: "Acciones de suscripciones y bolsas", onPress: openActions }, identityVisible: compactHeaderVisible, mode: "default", title: "Elige un plan" }
      : { action: { icon: "more", label: "Acciones de suscripciones y bolsas", onPress: openActions }, fallback: "/account", identityVisible: compactHeaderVisible, mode: "back", title: "Suscripciones y Bolsas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, isOnboarding, openActions, setHeaderPresentation]));
  useFocusEffect(useCallback(() => { void load(); }, [load]));
  const clearNotices = useCallback(() => {
    setRestoreNotice(null);
    setLocalError(null);
    coordinator?.clearMessages();
  }, [coordinator]);
  useFocusEffect(useCallback(() => {
    screenFocused.current = true;
    noticeGeneration.current += 1;
    clearNotices();
    return () => {
      screenFocused.current = false;
      noticeGeneration.current += 1;
      clearNotices();
    };
  }, [clearNotices]));
  useEffect(() => {
    if (isOnboarding && billing?.state.phase === "active" && billing.state.message) {
      void finishOnboarding().catch((nextError) => setLocalError(userFacingError(nextError)));
    }
  }, [billing?.state.message, billing?.state.phase, finishOnboarding, isOnboarding]);

  useFocusEffect(useCallback(() => {
    if (connected && refreshCatalog) void refreshCatalog();
  }, [connected, refreshCatalog]));

  const buy = (productId: string, basePlanId = "", pack = false) => {
    noticeGeneration.current += 1;
    clearNotices();
    return billing?.buy(productId, basePlanId, pack);
  };
  const buyCreditPack = (productId: string) => buy(productId, "", true);
  const restore = async () => {
    if (!billing || working) return;
    const generation = ++noticeGeneration.current;
    clearNotices();
    try {
      const result = await billing.restore();
      if (!screenFocused.current || generation !== noticeGeneration.current) return;
      if (result) setRestoreNotice(result.found === 0
        ? "No hay compras pendientes de restaurar. Las bolsas acreditadas permanecen en tu saldo."
        : result.verified < result.found
          ? "Algunas compras no pudieron verificarse o pertenecen a otra cuenta. Revisa tu plan y saldo; puedes reintentar más tarde."
          : "Revisamos tus compras. Tu plan y saldo muestran los beneficios actuales.");
    } catch (nextError) {
      if (screenFocused.current && generation === noticeGeneration.current) setLocalError(storeBillingError(nextError, "restore", Platform.OS === "android" ? "Google Play" : "Apple"));
    }
  };
  const continueWithFree = async () => {
    if (purchaseBlocked) return;
    setLocalWorking(true);
    setLocalError(null);
    try { await finishOnboarding(); }
    catch (nextError) { setLocalError(userFacingError(nextError)); }
    finally { setLocalWorking(false); }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Revisando tu suscripción…" />;
  if (!overview) return <Screen headerMode="preserve">
    <InlineNotice tone="error">{error ?? "No pudimos consultar tu suscripción."}</InlineNotice>
    <Button label="Reintentar" onPress={() => void load()} />
  </Screen>;

  const storeProvider = Platform.OS === "android" ? "google_play" : "apple_app_store";
  const subscriptionPlans = ["Basic", "Pro"].map((planName) => ({
    planName,
    products: (overview?.products ?? [])
      .filter((item) => item.provider === storeProvider && item.plan_name.trim().toLowerCase() === planName.toLowerCase())
      .sort((left, right) => (left.interval === "month" ? 0 : 1) - (right.interval === "month" ? 0 : 1)),
  })).filter((plan) => plan.products.length > 0);

  return (
    <>
      <Stack.Screen options={{ headerShown: !isOnboarding }} />
      <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      {isOnboarding ? (
        <View style={styles.onboardingIntro}>
          <View style={styles.onboardingLogo}><MyScoopeBrandLogo /></View>
          <Text style={styles.onboardingTitle}>Elige un plan</Text>
          <Text style={styles.onboardingDescription}>Compara lo que incluyen Free, Basic y Pro.{"\n"}Puedes cambiar de plan más adelante.</Text>
        </View>
      ) : (
        <View style={styles.subscriptionHeader}>
          <View style={styles.subscriptionLogo}><MyScoopeBrandLogo compact /></View>
          <View style={styles.subscriptionTitleSpacing}>
            <AppHeader alignment="center" title="Suscripciones y Bolsas" />
          </View>
          <View style={styles.subscriptionDescriptionGroup}>
            <Text style={styles.subscriptionDescription}>Nuestras suscripciones te entregan beneficios para enriquecer tus librerías y facilitar tu gestión nutricional.</Text>
            <Text style={styles.subscriptionDescription}>Con Basic o Pro puedes comprar bolsas para asistencia adicional. El saldo comprado permanece disponible si cambias de plan, incluso al volver a Free.</Text>
          </View>
        </View>
      )}
      {error ? <>
        <InlineNotice tone="error">{error}</InlineNotice>
        <Button disabled={working} label="Reintentar actualización" onPress={() => void load()} variant="secondary" />
      </> : null}
      {billing?.catalogError ? <>
        <Button disabled={working} label="Reintentar precios" loading={billing.catalogBusy} onPress={() => void refreshCatalog?.()} variant="secondary" />
      </> : null}
      {purchaseNotice && !activatingPlan ? <InlineNotice>{purchaseNotice}</InlineNotice> : null}
      {overview.evidence.some((item) => item.status === "authorized" && item.cancel_at_period_end) ?
        <InlineNotice>La renovación está desactivada. Tus beneficios actuales siguen disponibles hasta el final del periodo.</InlineNotice> : null}
      {billing?.state.finishPending ? <InlineNotice>Los beneficios verificados están guardados. La tienda aún debe cerrar la transacción; puedes reintentar con Restaurar compras.</InlineNotice> : null}
      {billing?.state.phase === "pending" ? <Button label="Reintentar verificación" onPress={() => void restore()} variant="secondary" /> : null}
      {restoreNotice ? <InlineNotice>{restoreNotice}</InlineNotice> : null}
      {creditBlocked ? <InlineNotice tone="warning">{entitlements?.credit_status === "frozen"
        ? "Los créditos están en revisión. Contacta al centro de soporte para continuar."
        : "Una tarea anterior debe finalizar antes de actualizar la disponibilidad de tus créditos."}</InlineNotice> : null}
      {creditBlocked ? <Button label="Actualizar saldo" onPress={() => void load()} variant="secondary" /> : null}
      {overview?.duplicate_active_providers ? (
        <InlineNotice tone="warning">Detectamos más de un canal de cobro activo. El equipo puede revisarlo sin interrumpir tu acceso.</InlineNotice>
      ) : null}
      {activatingPlan ? <Card accent={subscriptionPlanAccent(activatingPlan)}>
        <Text style={styles.eyebrow}>COMPRA CONFIRMADA POR LA TIENDA</Text>
        <SectionTitle title={`Plan ${activatingPlan}`} />
        <Text style={textStyles.muted}>{purchaseNotice}</Text>
      </Card> : !isOnboarding ? <Card accent={subscriptionPlanAccent(entitlements?.plan_name ?? overview?.plan_name)}>
        {entitlements ? <CreditDashboardGrid availableCredits={entitlements.available_credits} planName={entitlements.plan_name} /> : null}
      </Card> : null}

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

      {overview?.eligible && isOnboarding ? (
        <SubscriptionPlanCard accent={tokens.color.fat} benefits={commercialPlanBenefits.Free} caption="Incluido sin costo." name="Free" price="Gratis">
          <SubscriptionPurchaseButton disabled={purchaseBlocked} label="Continuar con Free" loading={working} onPress={() => void continueWithFree()} />
        </SubscriptionPlanCard>
      ) : null}

      {overview?.purchases_enabled && (Platform.OS === "ios" || Platform.OS === "android") ? (
        <>
          {!isOnboarding ? <SectionTitle title="Suscripciones disponibles" titleStyle={styles.commercialSectionTitle} /> : null}
          <View style={styles.commercialCardList}>
            {!isOnboarding ? <SubscriptionPlanCard accent={tokens.color.fat} benefits={commercialPlanBenefits.Free} caption="Incluido sin costo." name="Free" price="Gratis" /> : null}
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
                      disabled={purchaseBlocked || !connected || !storeProduct || (Platform.OS === "android" && !androidOffer)}
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
          </View>
          <Card style={styles.subscriptionInformationCard}>
            <SectionTitle title="Información de la suscripción" />
            <Text style={textStyles.muted}>{Platform.OS === "android"
              ? "El cobro se realiza a tu cuenta de Google Play al confirmar. La suscripción se renueva automáticamente por el mismo periodo y precio vigente hasta que la canceles desde tu cuenta de Google Play."
              : "El cobro se realiza a tu cuenta de App Store al confirmar. La suscripción se renueva automáticamente por el mismo periodo y precio vigente hasta que la canceles desde tu cuenta de Apple. Puedes cancelarla al menos 24 horas antes del término del periodo actual."}</Text>
            <Text style={textStyles.caption}>La compra habilita las funciones y créditos incluidos en el plan seleccionado en todos tus dispositivos donde uses la misma cuenta de My Scoope.</Text>
            <Button label="Política de privacidad" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/privacy/`)} variant="secondary" />
            <Button label="Términos de uso" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/terms/`)} variant="secondary" />
            <Button label="Cancelaciones y reembolsos" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/refund-policy/`)} variant="secondary" />
          </Card>
        </>
      ) : null}

      {!isOnboarding && overview?.can_buy_credit_packs && overview.credit_packs.length ? (
        <>
          <SectionDivider />
          <SectionHeading
            icon={<Sparkles color={tokens.color.entityIconForeground} size={18} />}
            title="Bolsas de créditos"
            titleStyle={styles.commercialSectionTitle}
          />
          <Text style={textStyles.muted}>Compra disponible en Basic y Pro.</Text>
          <View style={styles.commercialCardList}>
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
                    disabled={purchaseBlocked || !connected || !storeProduct}
                    label={`Comprar ${configured.credits.toLocaleString("es-CL")} créditos`}
                    loading={working}
                    onPress={() => void buyCreditPack(configured.product_id)}
                  />
                </Card>
              );
            })}
          </View>
        </>
      ) : null}

      <ActionSheetModal onRequestClose={closeActions} visible={actionsVisible}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
          <ActionSheetHeader icon={WalletCards} onClose={closeActions} title={pricesVisible ? "Diagnóstico de precios" : "Suscripciones y Bolsas"} />
          <View style={styles.sheetContent}>
            {pricesVisible ? <ScrollView showsVerticalScrollIndicator={false} style={{ maxHeight: 420 }}>
              <Button label="Copiar diagnóstico" onPress={() => void Clipboard.setStringAsync(JSON.stringify(billing?.priceDiagnostics(), null, 2))} variant="secondary" />
              <Text selectable style={textStyles.caption}>{JSON.stringify(billing?.priceDiagnostics(), null, 2)}</Text>
            </ScrollView> :
            <ActionSheetActions>
              <ActionSheetAction icon={Info} label="Ver detalles de Suscripciones y Bolsas" onPress={() => { closeActions(); router.push("/subscription-details" as Href); }} />
              <ActionSheetAction disabled={working} icon={RefreshCcw} label="Restaurar compras" onPress={() => { closeActions(); void restore(); }} />
              {billing?.canInspectPrices ? <ActionSheetAction icon={Info} label="Diagnóstico de precios" onPress={() => setPricesVisible(true)} /> : null}
            </ActionSheetActions>}
          </View>
        </SafeAreaView>
      </ActionSheetModal>
      </Screen>
    </>
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
  closeButton: { alignItems: "center", height: 40, justifyContent: "center", width: 40 },
  commercialCardList: { gap: 36 },
  commercialSectionTitle: { fontSize: tokens.type.section, lineHeight: 26 },
  creditPackPriceChip: { overflow: "hidden" },
  row: { alignItems: "center", flexDirection: "row", gap: 16, justifyContent: "space-between" },
  copy: { flex: 1, gap: 4 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  onboardingDescription: { color: tokens.color.textMuted, fontSize: 18, lineHeight: 25, textAlign: "center" },
  onboardingIntro: { alignItems: "center", gap: tokens.spacing.lg, paddingBottom: tokens.spacing.sm, paddingTop: tokens.spacing.lg },
  onboardingLogo: { marginBottom: tokens.spacing.lg },
  onboardingTitle: { color: tokens.color.textMain, fontSize: 34, fontWeight: tokens.weight.extraBold, lineHeight: 40, textAlign: "center" },
  planPriceChip: { alignItems: "center", borderRadius: tokens.radius.pill, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.xs },
  planPriceChipLabel: { color: tokens.color.surfaceApp, fontSize: 16, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  productName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, overflow: "hidden" },
  subscriptionHeader: { paddingBottom: tokens.spacing.lg },
  subscriptionDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 24, textAlign: "center" },
  subscriptionDescriptionGroup: { gap: tokens.spacing.md, marginTop: tokens.spacing.lg },
  subscriptionLogo: { alignItems: "center" },
  subscriptionTitleSpacing: { marginTop: 20 },
  subscriptionInformationCard: { marginTop: tokens.spacing.lg },
});
