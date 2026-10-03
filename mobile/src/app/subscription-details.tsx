import { Redirect, useFocusEffect } from "expo-router";
import { deepLinkToSubscriptions } from "expo-iap";
import { useCallback, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SubscriptionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Screen, SectionTitle, textStyles } from "@/components/ui";

const providerLabels: Record<string, string> = {
  apple_app_store: "App Store",
  google_play: "Google Play",
  paddle: "Paddle",
};

export default function SubscriptionDetailsScreen() {
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [overview, setOverview] = useState<SubscriptionData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/subscription", mode: "back", title: "Detalles de suscripciones y bolsas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Cargando detalles…" />;

  const manage = async () => {
    try {
      await deepLinkToSubscriptions();
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  };

  return (
    <Screen headerMode="preserve">
      <AppHeader eyebrow="Suscripciones y Bolsas" title="Detalles" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <Card muted>
        <SectionTitle title="Tu canal de compra" />
        <Text style={textStyles.muted}>Tu acceso funciona con la misma cuenta en todas las plataformas. Las cancelaciones y reembolsos se administran en el canal donde realizaste la compra.</Text>
      </Card>
      <Card muted>
        <SectionTitle title="Canales de cobro registrados" />
        <Text style={textStyles.muted}>Estos canales corresponden a compras de tu cuenta y no cambian la tienda de las compras nuevas.</Text>
        {overview?.evidence.length ? overview.evidence.map((item, index) => (
          <View key={`${item.provider}-${index}`} style={styles.row}>
            <Text style={textStyles.body}>{providerLabels[item.provider] ?? "Proveedor de pago"}</Text>
            <Text style={textStyles.caption}>{item.status}</Text>
          </View>
        )) : <Text style={textStyles.caption}>No hay canales de cobro registrados.</Text>}
        {Platform.OS === "ios" && overview?.evidence.some((item) => item.provider === "apple_app_store") ? (
          <Button label="Gestionar en App Store" onPress={() => void manage()} variant="secondary" />
        ) : null}
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", flexDirection: "row", gap: 16, justifyContent: "space-between" },
});
