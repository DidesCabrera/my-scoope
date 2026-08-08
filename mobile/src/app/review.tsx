import * as Crypto from "expo-crypto";
import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizationReview, ReviewInput, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, ChoiceRow, Field, InlineNotice, LoadingState, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type Score = "1" | "2" | "3" | "4" | "5";
const scoreOptions: { value: Score; label: string }[] = [1, 2, 3, 4, 5].map((value) => ({
  value: String(value) as Score,
  label: String(value),
}));

function subtractDays(value: string, days: number): string {
  const date = new Date(`${value}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

export default function ReviewScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [energy, setEnergy] = useState<Score>("3");
  const [hunger, setHunger] = useState<Score>("3");
  const [performance, setPerformance] = useState<Score>("3");
  const [note, setNote] = useState("");
  const [review, setReview] = useState<CalendarizationReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiRequest<TodayData>("/api/v1/today")
      .then(setToday)
      .catch((nextError) => setError(userFacingError(nextError)))
      .finally(() => setLoading(false));
  }, [apiRequest]);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando tu revisión…" />;

  async function submit() {
    if (!today?.calendarization) return;
    const candidateStart = subtractDays(today.local_date, 6);
    const payload: ReviewInput = {
      period_start: candidateStart < today.calendarization.start_date ? today.calendarization.start_date : candidateStart,
      period_end: today.local_date,
      idempotency_key: Crypto.randomUUID(),
      energy_score: Number(energy),
      hunger_score: Number(hunger),
      training_performance_score: Number(performance),
      note,
    };
    setSaving(true);
    setError(null);
    try {
      setReview(await apiRequest<CalendarizationReview>("/api/v1/program/reviews", {
        method: "POST",
        body: JSON.stringify(payload),
      }));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Programa vivido" title="Revisión de progreso" />
      <InlineNotice>La revisión congela lo ocurrido en este periodo. No cambia tu programa automáticamente.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!today?.calendarization ? (
        <Card><Text style={textStyles.muted}>Necesitas un programa calendarizado para registrar una revisión.</Text></Card>
      ) : review ? (
        <Card accent={tokens.color.success}>
          <Text style={styles.title}>Revisión registrada</Text>
          <Text style={textStyles.muted}>
            {review.summary_snapshot.adherence.adherence_percent}% de adherencia · {review.summary_snapshot.adherence.completed_meals} comidas cumplidas
          </Text>
          <Text style={textStyles.caption}>Esta evidencia podrá respaldar una propuesta futura, que siempre requerirá tu aprobación.</Text>
        </Card>
      ) : (
        <Card accent={tokens.color.program}>
          <ChoiceRow<Score> label="Energía general · 1 baja, 5 alta" onChange={setEnergy} options={scoreOptions} value={energy} />
          <ChoiceRow<Score> label="Hambre · 1 baja, 5 alta" onChange={setHunger} options={scoreOptions} value={hunger} />
          <ChoiceRow<Score> label="Rendimiento al entrenar" onChange={setPerformance} options={scoreOptions} value={performance} />
          <Field autoCapitalize="sentences" label="Nota opcional" onChangeText={setNote} placeholder="Sueño, entrenamiento o contexto relevante" value={note} />
          <Button label="Guardar revisión" loading={saving} onPress={() => void submit()} />
        </Card>
      )}
      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: tokens.color.textMain, fontSize: 21, fontWeight: "800" },
});
