import { type Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { ApiEnvelope, ShareClaimResult, ShareResource } from "@/api/types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, InlineNotice, Screen, SectionTitle, textStyles } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";

export default function SharedResourceScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [resource, setResource] = useState<ShareResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    void fetch(`${appConfig.apiBaseUrl}/api/v1/shares/${id}`)
      .then(async (response) => {
        const payload = await response.json() as ApiEnvelope<ShareResource>;
        if (!response.ok || !payload.ok) throw new Error(payload.ok ? "share_unavailable" : payload.error.message);
        if (active) setResource(payload.data);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (!id) return <Redirect href="/today" />;

  const claim = async () => {
    setClaiming(true);
    setError(null);
    try {
      await apiRequest<ShareClaimResult>(`/api/v1/shares/${id}/claims`, { method: "POST" });
      setClaimed(true);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setClaiming(false);
    }
  };

  const snapshot = resource?.snapshot;
  return (
    <Screen>
      <AppHeader eyebrow="Compartido contigo" title={resource?.title ?? "Plan diario"} />
      {loading ? <Text style={textStyles.muted}>Cargando contenido compartido…</Text> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {snapshot ? (
        <>
          <Card accent={tokens.color.dailyPlan}>
            <Text style={styles.calories}>{snapshot.nutrition.calories.toFixed(0)} kcal</Text>
            <View style={styles.macros}>
              <Text style={styles.macro}>P {snapshot.nutrition.protein_grams.toFixed(1)} g</Text>
              <Text style={styles.macro}>C {snapshot.nutrition.carbs_grams.toFixed(1)} g</Text>
              <Text style={styles.macro}>G {snapshot.nutrition.fat_grams.toFixed(1)} g</Text>
            </View>
            <Text style={textStyles.muted}>{snapshot.summary.meal_count} comidas · {snapshot.summary.food_count} alimentos</Text>
          </Card>
          <Card>
            <SectionTitle detail={`${snapshot.meals.length}`} title="Comidas" />
            {snapshot.meals.map((meal, index) => (
              <View key={`${meal.name}-${index}`} style={styles.meal}>
                <View style={styles.mealHeading}><Text style={styles.mealName}>{meal.name}</Text><Text style={textStyles.caption}>{meal.time ?? "Sin hora"}</Text></View>
                <Text style={textStyles.muted}>{meal.nutrition.calories.toFixed(0)} kcal · {meal.foods.length} alimentos</Text>
              </View>
            ))}
          </Card>
          {claimed ? (
            <>
              <InlineNotice>El plan está disponible en tu Inbox.</InlineNotice>
              <Button label="Ir al Inbox" onPress={() => router.replace("/inbox" as Href)} />
            </>
          ) : status === "anonymous" ? (
            <Button label="Iniciar sesión para agregar" onPress={() => router.push({ pathname: "/login", params: { returnTo: `/share/${id}` } })} />
          ) : resource?.claim_policy === "none" ? (
            <InlineNotice>Este enlace es sólo de lectura.</InlineNotice>
          ) : (
            <Button label="Agregar a mi Inbox" loading={claiming} onPress={() => void claim()} />
          )}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  calories: { color: tokens.color.textMain, fontSize: 34, fontWeight: "900" },
  macro: { color: tokens.color.textMain, fontSize: 14, fontWeight: "800" },
  macros: { flexDirection: "row", gap: tokens.spacing.lg },
  meal: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.xs, paddingTop: tokens.spacing.md },
  mealHeading: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  mealName: { color: tokens.color.textMain, fontSize: 16, fontWeight: "800" },
});
