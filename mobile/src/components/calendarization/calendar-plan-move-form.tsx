import * as Crypto from "expo-crypto";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarDayDetailData } from "@/api/types";
import { Button, InlineNotice, NativeDateTimeField } from "@/components/ui";
import { tokens } from "@/design/tokens";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function CalendarPlanMoveForm({ apiRequest, localToday, name, onCancel, onMoved, sourceDate }: {
  apiRequest: ApiRequest;
  localToday: string;
  name: string;
  onCancel(): void;
  onMoved(): Promise<void> | void;
  sourceDate: string;
}) {
  const [targetDate, setTargetDate] = useState(sourceDate);
  const [target, setTarget] = useState<CalendarDayDetailData | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function review() {
    if (targetDate < localToday || targetDate === sourceDate || reviewing) return;
    setReviewing(true);
    setError(null);
    try {
      setTarget(await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${targetDate}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setReviewing(false);
    }
  }

  async function move() {
    if (!target || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest(`/api/v1/calendar/days/${sourceDate}/move`, {
        body: JSON.stringify({ target_date: targetDate, assignment_key: Crypto.randomUUID(), replace_existing: target.has_plan }),
        method: "POST",
      });
      await onMoved();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }

  return <View style={styles.form}>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {target ? <>
      <Text style={styles.message}>{target.has_plan
        ? `“${name}” pasará al ${targetDate}. “${target.plan_name}” conservará su historial y dejará de estar vigente en esa fecha.`
        : `“${name}” pasará al ${targetDate}. La fecha original quedará libre y su historial permanecerá guardado.`}</Text>
      {target.has_execution ? <InlineNotice tone="error">La fecha de destino ya tiene cumplimiento registrado y no se puede reemplazar.</InlineNotice> : null}
      <Button disabled={target.has_execution} label="Mover minuta" loading={submitting} onPress={() => void move()} />
      <Button disabled={submitting} label="Cambiar fecha" onPress={() => setTarget(null)} variant="secondary" />
    </> : <>
      <NativeDateTimeField label="Nueva fecha" minimumValue={localToday} mode="date" onChange={setTargetDate} value={targetDate} />
      <Button disabled={reviewing || targetDate < localToday || targetDate === sourceDate} label="Revisar movimiento" loading={reviewing} onPress={() => void review()} />
      <Button disabled={reviewing} label="Cancelar" onPress={onCancel} variant="secondary" />
    </>}
  </View>;
}

const styles = StyleSheet.create({
  form: { gap: tokens.spacing.md },
  message: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, marginBottom: 18 },
});
