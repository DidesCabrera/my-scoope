import { Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MealCheckInInput, MealExecutionStatus, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function CheckInScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

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
  const executionByKey = new Map((today?.meal_execution ?? []).map((item) => [item.meal_key, item]));

  async function checkIn(mealKey: string, action: MealCheckInInput["action"]) {
    if (!today?.day_id) return;
    setSavingKey(mealKey);
    setError(null);
    try {
      const payload: MealCheckInInput = {
        action,
        idempotency_key: Crypto.randomUUID(),
      };
      const updated = await apiRequest<TodayData>(
        `/api/v1/days/${today.day_id}/meals/${encodeURIComponent(mealKey)}/check-ins`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      setToday(updated);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSavingKey(null);
    }
  }

  function statusLabel(status: MealExecutionStatus): string {
    if (status === "completed") return "Cumplida";
    if (status === "skipped") return "Omitida";
    return "Pendiente";
  }
  return (
    <Screen>
      <AppHeader eyebrow="Ejecución diaria" title="Check-in del día" />
      <InlineNotice>Cada acción agrega evidencia al día calendarizado. Si corriges una acción, el historial anterior se conserva.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {meals.map((meal, index) => {
        const mealKey = meal.key ?? "";
        const execution = executionByKey.get(mealKey);
        const status = execution?.status ?? "planned";
        const statusColor = status === "completed" ? tokens.color.success : status === "skipped" ? tokens.color.warning : tokens.color.textSoft;
        return (
          <Card key={meal.key ?? `${meal.name}-${index}`} muted style={styles.meal}>
            <View style={styles.row}>
              <View style={styles.number}><Text style={styles.numberText}>{index + 1}</Text></View>
              <View style={styles.copy}>
                <Text style={styles.name}>{meal.name ?? "Comida"}</Text>
                <Text style={textStyles.caption}>{meal.hour ? `Prevista a las ${meal.hour}` : "Sin horario previsto"}</Text>
              </View>
              <Pill color={statusColor} label={statusLabel(status)} />
            </View>
            <Text style={textStyles.muted}>{meal.foods?.map((food) => food.name).filter(Boolean).join(" · ") || "Sin alimentos en el snapshot"}</Text>
            {status === "planned" ? (
              <View style={styles.actions}>
                <View style={styles.action}><Button disabled={!mealKey || savingKey !== null} label="Cumplida" loading={savingKey === mealKey} onPress={() => void checkIn(mealKey, "completed")} /></View>
                <View style={styles.action}><Button disabled={!mealKey || savingKey !== null} label="Omitida" onPress={() => void checkIn(mealKey, "skipped")} variant="secondary" /></View>
              </View>
            ) : (
              <Button disabled={savingKey !== null} label="Corregir a pendiente" loading={savingKey === mealKey} onPress={() => void checkIn(mealKey, "reset")} variant="secondary" />
            )}
          </Card>
        );
      })}
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
  actions: { flexDirection: "row", gap: tokens.spacing.sm },
  action: { flex: 1 },
});
