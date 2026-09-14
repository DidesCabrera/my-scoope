import { useFocusEffect } from "expo-router";
import * as Crypto from "expo-crypto";
import { Check, Pencil } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MealCheckInInput, MealExecutionItem, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, ContentPanel, InlineNotice, SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { MealCompletionSurface } from "./meal-completion-summary";

type Props = { dayId?: number; enabled?: boolean; mealKey: string; mode?: "calendarized" | "pinned"; onChange?: (execution: MealExecutionItem) => void };

function executionFor(data: TodayData, { dayId, mealKey, mode = "calendarized" }: Props): MealExecutionItem | null {
  const available = mode === "pinned"
    ? data.calendarization == null && data.pinned_plan?.panel.meals.some((meal) => meal.id === mealKey)
    : data.day_id === dayId && data.plan_snapshot?.meals?.some((meal) => meal.key === mealKey);
  if (!available) return null;
  return data.meal_execution.find((item) => item.meal_key === mealKey) ?? {
    meal_key: mealKey, status: "planned", last_event_id: null, recorded_at: null, note: "", prepared_food_keys: [],
  };
}

export function useMealAdherenceCheckIn({ dayId, enabled = true, mealKey, mode = "calendarized", onChange }: Props) {
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
    const execution = executionFor(data, { dayId, mealKey, mode });
    setAvailable(execution != null);
    if (!execution) return;
    setCompleted(execution.status === "completed");
    setNote(execution.note);
    onChange?.(execution);
  }, [dayId, mealKey, mode, onChange]);

  useFocusEffect(useCallback(() => {
    if (!enabled || status !== "authenticated") {
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
        const execution = executionFor(data, { dayId, mealKey, mode });
        applyToday(data);
        setEditingNote(!execution?.note.trim());
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, applyToday, dayId, enabled, mealKey, mode, status]));

  const checkInPath = mode === "pinned"
    ? `/api/v1/today/pinned-plan/meals/${encodeURIComponent(mealKey)}/check-ins`
    : `/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`;

  async function saveStatus(nextCompleted: boolean) {
    const previousCompleted = completed;
    setCompleted(nextCompleted);
    setSavingStatus(true);
    setError(null);
    try {
      const payload: MealCheckInInput = { action: nextCompleted ? "completed" : "skipped", idempotency_key: Crypto.randomUUID() };
      applyToday(await apiRequest<TodayData>(checkInPath, { method: "POST", body: JSON.stringify(payload) }));
    } catch (nextError) { setCompleted(previousCompleted); setError(userFacingError(nextError)); }
    finally { setSavingStatus(false); }
  }

  async function saveNote() {
    setSavingNote(true);
    setError(null);
    try {
      const payload: MealCheckInInput = { action: "note", idempotency_key: Crypto.randomUUID(), note };
      applyToday(await apiRequest<TodayData>(checkInPath, { method: "POST", body: JSON.stringify(payload) }));
      setEditingNote(false);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSavingNote(false); }
  }

  return { available: !loading && available, completed, editingNote, error, note, saveNote, saveStatus, savingNote, savingStatus, setEditingNote, setNote };
}

export type MealAdherenceController = ReturnType<typeof useMealAdherenceCheckIn>;

export function MealCompletionToggleCard({ available = true, completed, error, onToggle, saving = false }: { available?: boolean; completed: boolean; error?: string | null; onToggle(nextCompleted: boolean): void; saving?: boolean }) {
  if (!available) return null;
  return <MealCompletionSurface>
    <Pressable accessibilityLabel="Comida cumplida" accessibilityRole="checkbox" accessibilityState={{ checked: completed, disabled: saving }} disabled={saving} onPress={() => onToggle(!completed)} style={({ pressed }) => [styles.completionRow, saving && styles.saving, pressed && styles.pressed]}>
      <Text style={styles.completionLabel}>Comida cumplida</Text>
      <View style={[styles.checkbox, completed && styles.checkboxChecked]}>{completed ? <Check color={tokens.color.entityIconForeground} size={17} strokeWidth={3} /> : null}</View>
    </Pressable>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
  </MealCompletionSurface>;
}

export function MealCompletionCard({ controller }: { controller: MealAdherenceController }) {
  return <MealCompletionToggleCard available={controller.available} completed={controller.completed} error={controller.error} onToggle={(nextCompleted) => void controller.saveStatus(nextCompleted)} saving={controller.savingStatus} />;
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
  checkbox: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 2, height: 26, justifyContent: "center", width: 26 },
  checkboxChecked: { backgroundColor: tokens.color.meal, borderColor: tokens.color.meal },
  completionLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold, minWidth: 0 },
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
