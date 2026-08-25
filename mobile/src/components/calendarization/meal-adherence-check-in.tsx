import { useFocusEffect } from "expo-router";
import * as Crypto from "expo-crypto";
import { Check } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MealCheckInInput, MealExecutionItem, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, ContentPanel, InlineNotice, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { dayId: number; mealKey: string };

function executionFor(data: TodayData, dayId: number, mealKey: string): MealExecutionItem | null {
  if (data.day_id !== dayId || !data.plan_snapshot?.meals?.some((meal) => meal.key === mealKey)) return null;
  return data.meal_execution.find((item) => item.meal_key === mealKey) ?? {
    meal_key: mealKey,
    status: "planned",
    last_event_id: null,
    recorded_at: null,
    note: "",
  };
}

export function MealAdherenceCheckIn({ dayId, mealKey }: Props) {
  const { apiRequest } = useSession();
  const [available, setAvailable] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);
  const [statusSaved, setStatusSaved] = useState(false);

  const applyToday = useCallback((data: TodayData) => {
    const execution = executionFor(data, dayId, mealKey);
    setAvailable(execution != null);
    if (!execution) return;
    setCompleted(execution.status === "completed");
    setNote(execution.note);
  }, [dayId, mealKey]);

  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void apiRequest<TodayData>("/api/v1/today")
      .then((data) => { if (active) applyToday(data); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, applyToday]));

  async function saveStatus(nextCompleted: boolean) {
    const previousCompleted = completed;
    setCompleted(nextCompleted);
    setSavingStatus(true);
    setNoteSaved(false);
    setStatusSaved(false);
    setError(null);
    try {
      const payload: MealCheckInInput = {
        action: nextCompleted ? "completed" : "skipped",
        idempotency_key: Crypto.randomUUID(),
      };
      const updated = await apiRequest<TodayData>(
        `/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      applyToday(updated);
      setStatusSaved(true);
    } catch (nextError) {
      setCompleted(previousCompleted);
      setError(userFacingError(nextError));
    } finally {
      setSavingStatus(false);
    }
  }

  async function saveNote() {
    setSavingNote(true);
    setNoteSaved(false);
    setStatusSaved(false);
    setError(null);
    try {
      const payload: MealCheckInInput = {
        action: "note",
        idempotency_key: Crypto.randomUUID(),
        note,
      };
      const updated = await apiRequest<TodayData>(
        `/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      applyToday(updated);
      setNoteSaved(true);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSavingNote(false);
    }
  }

  if (loading || !available) return null;

  return (
    <ContentPanel muted title="Cumplimiento de esta comida">
      <Pressable
        accessibilityLabel="Comida cumplida"
        accessibilityRole="checkbox"
        accessibilityState={{ checked: completed, disabled: savingStatus }}
        disabled={savingStatus}
        onPress={() => void saveStatus(!completed)}
        style={({ pressed }) => [styles.completionRow, savingStatus && styles.saving, pressed && styles.pressed]}>
        <View style={styles.completionCopy}>
          <Text style={styles.completionLabel}>Comida cumplida</Text>
          <Text style={textStyles.caption}>Marca la casilla si cumpliste esta comida del programa.</Text>
        </View>
        <View style={[styles.checkbox, completed && styles.checkboxChecked]}>
          {completed ? <Check color={tokens.color.entityIconForeground} size={17} strokeWidth={3} /> : null}
        </View>
      </Pressable>

      <View style={styles.divider} />

      <View style={styles.noteBlock}>
        <View style={styles.noteHeader}>
          <Text style={styles.noteLabel}>Nota</Text>
          <Text style={styles.noteCount}>{note.length}/500</Text>
        </View>
        <TextInput
          accessibilityLabel="Nota sobre el cumplimiento de la comida"
          maxLength={500}
          multiline
          onChangeText={(value) => { setNote(value); setNoteSaved(false); }}
          placeholder="Escribe una observación opcional…"
          placeholderTextColor={tokens.color.textMuted}
          style={styles.noteInput}
          textAlignVertical="top"
          value={note}
        />
      </View>

      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {statusSaved ? <InlineNotice>Cumplimiento actualizado.</InlineNotice> : null}
      {noteSaved ? <InlineNotice>Nota guardada.</InlineNotice> : null}
      <Button label="Guardar nota" loading={savingNote} onPress={() => void saveNote()} />
    </ContentPanel>
  );
}

const styles = StyleSheet.create({
  checkbox: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.sm, borderWidth: 2, height: 26, justifyContent: "center", width: 26 },
  checkboxChecked: { backgroundColor: tokens.color.meal, borderColor: tokens.color.meal },
  completionCopy: { flex: 1, gap: 2, minWidth: 0 },
  completionLabel: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  completionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  divider: { backgroundColor: tokens.color.borderSoft, height: 1 },
  noteBlock: { gap: tokens.spacing.xs },
  noteCount: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  noteHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  noteInput: { backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, fontSize: tokens.type.caption, minHeight: 104, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  noteLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  pressed: { opacity: 0.65 },
  saving: { opacity: 0.75 },
});
