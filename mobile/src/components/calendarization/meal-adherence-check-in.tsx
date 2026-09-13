import { useFocusEffect } from "expo-router";
import * as Crypto from "expo-crypto";
import { Check, Pencil } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MealCheckInInput, MealExecutionItem, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, ContentPanel, InlineNotice, SectionHeading, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { dayId: number; mealKey: string; onChange?: (execution: MealExecutionItem) => void };

function executionFor(data: TodayData, dayId: number, mealKey: string): MealExecutionItem | null {
  if (data.day_id !== dayId || !data.plan_snapshot?.meals?.some((meal) => meal.key === mealKey)) return null;
  return data.meal_execution.find((item) => item.meal_key === mealKey) ?? {
    meal_key: mealKey, status: "planned", last_event_id: null, recorded_at: null, note: "", prepared_food_keys: [],
  };
}

export function useMealAdherenceCheckIn({ dayId, mealKey, onChange }: Props) {
  const { apiRequest, status } = useSession();
  const [available, setAvailable] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [editingNote, setEditingNote] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);

  const applyToday = useCallback((data: TodayData) => {
    const execution = executionFor(data, dayId, mealKey);
    setAvailable(execution != null);
    if (!execution) return;
    setCompleted(execution.status === "completed");
    setNote(execution.note);
    onChange?.(execution);
  }, [dayId, mealKey, onChange]);

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") {
      setLoading(false);
      setAvailable(false);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    void apiRequest<TodayData>("/api/v1/today")
      .then((data) => {
        if (!active) return;
        const execution = executionFor(data, dayId, mealKey);
        applyToday(data);
        setEditingNote(!execution?.note.trim());
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, applyToday, dayId, mealKey, status]));

  async function saveStatus(nextCompleted: boolean) {
    const previousCompleted = completed;
    setCompleted(nextCompleted);
    setSavingStatus(true);
    setError(null);
    try {
      const payload: MealCheckInInput = { action: nextCompleted ? "completed" : "skipped", idempotency_key: Crypto.randomUUID() };
      applyToday(await apiRequest<TodayData>(`/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`, { method: "POST", body: JSON.stringify(payload) }));
    } catch (nextError) { setCompleted(previousCompleted); setError(userFacingError(nextError)); }
    finally { setSavingStatus(false); }
  }

  async function saveNote() {
    setSavingNote(true);
    setError(null);
    try {
      const payload: MealCheckInInput = { action: "note", idempotency_key: Crypto.randomUUID(), note };
      applyToday(await apiRequest<TodayData>(`/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`, { method: "POST", body: JSON.stringify(payload) }));
      setEditingNote(false);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSavingNote(false); }
  }

  return { available: !loading && available, completed, editingNote, error, note, saveNote, saveStatus, savingNote, savingStatus, setEditingNote, setNote };
}

export type MealAdherenceController = ReturnType<typeof useMealAdherenceCheckIn>;

export function MealCompletionCard({ controller }: { controller: MealAdherenceController }) {
  if (!controller.available) return null;
  return <ContentPanel muted>
    <Pressable accessibilityLabel="Comida cumplida" accessibilityRole="checkbox" accessibilityState={{ checked: controller.completed, disabled: controller.savingStatus }} disabled={controller.savingStatus} onPress={() => void controller.saveStatus(!controller.completed)} style={({ pressed }) => [styles.completionRow, controller.savingStatus && styles.saving, pressed && styles.pressed]}>
      <View style={styles.completionCopy}><Text style={styles.completionLabel}>Comida cumplida</Text><Text style={textStyles.caption}>Marca la casilla si cumpliste esta comida del programa.</Text></View>
      <View style={[styles.checkbox, controller.completed && styles.checkboxChecked]}>{controller.completed ? <Check color={tokens.color.entityIconForeground} size={17} strokeWidth={3} /> : null}</View>
    </Pressable>
    {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
  </ContentPanel>;
}

export function MealNoteCard({ controller }: { controller: MealAdherenceController }) {
  if (!controller.available) return null;
  return <View style={styles.section}>
    <SectionHeading title="Nota de esta comida" />
    <ContentPanel muted>
      <View style={styles.noteBlock}>
        <View style={styles.noteHeader}>
          <Text style={styles.noteLabel}>Nota</Text>
          {controller.editingNote ? <Text style={styles.noteCount}>{controller.note.length}/500</Text> : <Pressable accessibilityLabel="Editar nota" accessibilityRole="button" hitSlop={8} onPress={() => controller.setEditingNote(true)} style={({ pressed }) => [styles.noteEdit, pressed && styles.pressed]}><Pencil color={tokens.color.textMuted} size={18} strokeWidth={2.2} /></Pressable>}
        </View>
        {controller.editingNote ? <TextInput accessibilityLabel="Nota sobre el cumplimiento de la comida" maxLength={500} multiline onChangeText={controller.setNote} placeholder="Escribe una observación opcional…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={controller.note} /> : <Text style={[styles.noteText, !controller.note.trim() && styles.noteTextEmpty]}>{controller.note.trim() || "Sin nota registrada."}</Text>}
      </View>
      {controller.error ? <InlineNotice tone="error">{controller.error}</InlineNotice> : null}
      {controller.editingNote ? <Button label="Guardar nota" loading={controller.savingNote} onPress={() => void controller.saveNote()} /> : null}
    </ContentPanel>
  </View>;
}

export function MealAdherenceCheckIn(props: Props) {
  const controller = useMealAdherenceCheckIn(props);
  return <View style={styles.section}><MealCompletionCard controller={controller} /><MealNoteCard controller={controller} /></View>;
}

const styles = StyleSheet.create({
  checkbox: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.sm, borderWidth: 2, height: 26, justifyContent: "center", width: 26 },
  checkboxChecked: { backgroundColor: tokens.color.meal, borderColor: tokens.color.meal },
  completionCopy: { flex: 1, gap: 2, minWidth: 0 },
  completionLabel: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  completionRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  noteBlock: { gap: tokens.spacing.xs },
  noteCount: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  noteEdit: { alignItems: "center", height: 32, justifyContent: "center", width: 32 },
  noteHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  noteInput: { backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, fontSize: tokens.type.caption, minHeight: 104, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  noteLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  noteText: { color: tokens.color.textMain, fontSize: tokens.type.caption, lineHeight: 21, minHeight: 42 },
  noteTextEmpty: { color: tokens.color.textMuted },
  pressed: { opacity: 0.65 }, saving: { opacity: 0.75 }, section: { gap: tokens.spacing.sm, minWidth: 0 },
});
