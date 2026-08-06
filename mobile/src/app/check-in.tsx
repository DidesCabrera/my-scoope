import { Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export default function CheckInScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      setLoading(true);
      void apiRequest<TodayData>("/api/v1/today")
        .then((data) => {
          if (active) setToday(data);
        })
        .catch((nextError) => {
          if (active) setError(userFacingError(nextError));
        })
        .finally(() => {
          if (active) setLoading(false);
        });
      return () => {
        active = false;
      };
    }, [apiRequest]),
  );

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando el check-in…" />;

  const meals = today?.plan_snapshot?.meals ?? [];
  return (
    <Screen>
      <AppHeader eyebrow="Ejecución diaria" title="Check-in del día" />
      <InlineNotice tone="warning">Esta pantalla valida la experiencia nativa de CML03. El registro durable de adherencia se habilitará en CML04 dentro del programa calendarizado.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {meals.map((meal, index) => (
        <Card key={meal.key ?? `${meal.name}-${index}`} muted style={styles.meal}>
          <View style={styles.row}>
            <View style={styles.number}><Text style={styles.numberText}>{index + 1}</Text></View>
            <View style={styles.copy}>
              <Text style={styles.name}>{meal.name ?? "Comida"}</Text>
              <Text style={textStyles.caption}>{meal.hour ? `Prevista a las ${meal.hour}` : "Sin horario previsto"}</Text>
            </View>
            <Pill color={tokens.color.textSoft} label="Pendiente" />
          </View>
          <Text style={textStyles.muted}>{meal.foods?.map((food) => food.name).filter(Boolean).join(" · ") || "Sin alimentos en el snapshot"}</Text>
          <Button disabled label="Registrar como cumplida" onPress={() => undefined} variant="secondary" />
        </Card>
      ))}
      {!meals.length ? (
        <Card><Text style={textStyles.muted}>No hay comidas previstas para registrar hoy.</Text></Card>
      ) : null}
      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  meal: { borderLeftColor: tokens.color.meal, borderLeftWidth: 3 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  number: { alignItems: "center", backgroundColor: tokens.color.meal, borderRadius: tokens.radius.md, height: 34, justifyContent: "center", width: 34 },
  numberText: { color: tokens.color.surfaceApp, fontSize: 15, fontWeight: "900" },
  copy: { flex: 1, gap: 2 },
  name: { color: tokens.color.textMain, fontSize: 17, fontWeight: "800" },
});
