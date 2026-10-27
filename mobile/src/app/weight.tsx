import { Redirect, useFocusEffect } from "expo-router";
import { Check, Pencil, Plus, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { WeightInput, WeightItem, WeightListData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, Card, CardHeader, Field, InlineNotice, KeyValueTable, LoadingState, NativeDateTimeField, NativeMeasurementField, Screen, SectionPageHeader, textStyles, WeightTrendCard } from "@/components/ui";
import { ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";
import { localDateValue, localTimeValue } from "@/presentation/date-time-values";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function historyDateLabel(item: WeightItem): string {
  const time = item.measured_time?.slice(0, 5);
  return time ? `${formatDate(item.measured_on)} · ${time}` : formatDate(item.measured_on);
}

function weightVariationLabel(current: WeightItem, previous?: WeightItem): string {
  if (!previous) return "—";
  const rawVariation = current.weight_kg - previous.weight_kg;
  const variation = Math.abs(rawVariation) < 0.05 ? 0 : rawVariation;
  const sign = variation > 0 ? "+" : "";
  return `${sign}${variation.toFixed(1).replace(".", ",")} kg`;
}

export default function WeightScreen() {
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<WeightItem[]>([]);
  const [value, setValue] = useState(profile?.current_weight_kg?.toString() ?? "");
  const [measuredTime, setMeasuredTime] = useState("");
  const [comment, setComment] = useState("");
  const [editingItem, setEditingItem] = useState<WeightItem | null>(null);
  const [historyFormMode, setHistoryFormMode] = useState<"create" | "edit" | null>(null);
  const [historyEditing, setHistoryEditing] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editDate, setEditDate] = useState(localDateValue());
  const [editTime, setEditTime] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const history = await apiRequest<WeightListData>("/api/v1/weights?limit=12");
      setItems(history.items);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/today", identityVisible: compactHeaderVisible, mode: "back", title: "Registra tu peso" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    void load();
  }, [load]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando tus mediciones…" />;

  async function save() {
    const weight = Number(value.replace(",", "."));
    if (!Number.isFinite(weight) || weight < 25 || weight > 350) {
      setError("Ingresa un peso válido entre 25 y 350 kg.");
      return;
    }
    const payload: WeightInput = { comment: comment.trim(), measured_on: localDateValue(), measured_time: measuredTime || localTimeValue(), weight_kg: weight };
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await apiRequest<WeightItem>("/api/v1/weights", { method: "POST", body: JSON.stringify(payload) });
      await Promise.all([load(), refreshProfile()]);
      setMeasuredTime("");
      setComment("");
      setSaved(true);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  function openEdit(item: WeightItem) {
    setEditingItem(item);
    setHistoryFormMode("edit");
    setEditValue(item.weight_kg.toFixed(1).replace(".", ","));
    setEditDate(item.measured_on);
    setEditTime(item.measured_time?.slice(0, 5) ?? "");
    setEditError(null);
  }

  function openCreate() {
    setEditingItem(null);
    setHistoryFormMode("create");
    setEditValue("");
    setEditDate("");
    setEditTime("");
    setEditError(null);
  }

  function closeEdit() {
    setEditingItem(null);
    setHistoryFormMode(null);
    setEditError(null);
  }

  async function saveHistory() {
    if (!historyFormMode) return;
    const weight = Number(editValue.replace(",", "."));
    if (!Number.isFinite(weight) || weight < 25 || weight > 350) {
      setEditError("Ingresa un peso válido entre 25 y 350 kg.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(editDate)) {
      setEditError("Selecciona la fecha de la medición.");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      const payload: WeightInput = { measured_on: editDate, measured_time: editTime || null, weight_kg: weight };
      if (historyFormMode === "edit" && editingItem) {
        await apiRequest<WeightItem>(`/api/v1/weights/${editingItem.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await apiRequest<WeightItem>("/api/v1/weights", { method: "POST", body: JSON.stringify(payload) });
      }
      await Promise.all([load(), refreshProfile()]);
      closeEdit();
      setSaved(true);
    } catch (nextError) {
      setEditError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  async function deleteWeight(item: WeightItem) {
    setDeletingId(item.id);
    setSaved(false);
    try {
      await apiRequest<{ deleted_id: number }>(`/api/v1/weights/${item.id}`, { method: "DELETE" });
      await Promise.all([load(), refreshProfile()]);
    } catch (nextError) {
      Alert.alert("No pudimos eliminar la medición", userFacingError(nextError));
    } finally {
      setDeletingId(null);
    }
  }

  function confirmDeleteWeight(item: WeightItem) {
    Alert.alert(
      "Eliminar medición",
      `¿Eliminar la medición de ${item.weight_kg.toFixed(1)} kg del ${historyDateLabel(item)}?`,
      [
        { text: "Cancelar", style: "cancel" },
        { text: "Eliminar", style: "destructive", onPress: () => void deleteWeight(item) },
      ],
    );
  }

  return (
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      <SectionPageHeader countLabel="mediciones" section="weight" subtitle="El registro de peso te permitirá visualizar su variación. Esto revelará tendencias en el mediano y largo plazo." title="Registra tu peso" />
      <Card accent={tokens.color.protein}>
        <CardHeader title="Registro de peso actual" />
        <Text style={textStyles.muted}>Mídete en condiciones similares para que la tendencia sea comparable.</Text>
        <NativeMeasurementField kind="weight" label={`Peso actual · ${formatDate(localDateValue())}`} onChange={setValue} value={value} />
        <NativeDateTimeField label="Hora de medición (Opcional)" mode="time" onChange={setMeasuredTime} value={measuredTime} />
        <Field autoCapitalize="sentences" label="Comentario (Opcional)" maxLength={500} onChangeText={setComment} placeholder="Agrega contexto sobre esta medición" value={comment} />
        <View style={styles.saveButtonSpacing}>
          <Button label="Guardar medición" loading={saving} onPress={save} />
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {saved ? <InlineNotice>Medición guardada. Tu Today ya usa el peso actualizado.</InlineNotice> : null}
      </Card>
      <InlineNotice>
        La variación de peso puede deberse a diferentes factores, destacando la variación de agua en el cuerpo, la cual puede cambiar en un corto lapso de tiempo.{"\n\n"}
        Por eso te aconsejamos evaluar la tendencia en el mediano plazo, más que dentro de uno o pocos días.
      </InlineNotice>
      <WeightTrendCard items={items} />
      <Card>
        <CardHeader
          accessory={<View style={styles.historyActions}>
            <Pressable
              accessibilityLabel="Agregar medición anterior"
              accessibilityRole="button"
              onPress={openCreate}
              style={({ pressed }) => [styles.historyEditToggle, pressed && styles.pressed]}>
              <Plus color={tokens.color.textMain} size={23} strokeWidth={2.2} />
            </Pressable>
            <Pressable
              accessibilityLabel={historyEditing ? "Finalizar edición de pesos históricos" : "Editar pesos históricos"}
              accessibilityRole="button"
              onPress={() => setHistoryEditing((current) => !current)}
              style={({ pressed }) => [styles.historyEditToggle, pressed && styles.pressed]}>
              {historyEditing
                ? <Check color={tokens.color.textMain} size={22} strokeWidth={2.4} />
                : <Pencil color={tokens.color.textMain} size={20} strokeWidth={2.2} />}
            </Pressable>
          </View>}
          description={`${items.length} registros`}
          title="Pesos históricos"
        />
        {items.length ? (
          <KeyValueTable items={items.map((item, index) => ({
            accessory: historyEditing ? (
              <View style={styles.rowEditActions}>
                <Pressable
                  accessibilityLabel={`Editar peso del ${historyDateLabel(item)}`}
                  accessibilityRole="button"
                  disabled={deletingId != null}
                  hitSlop={8}
                  onPress={() => openEdit(item)}
                  style={({ pressed }) => [styles.rowEditAction, pressed && styles.pressed]}>
                  <Pencil color={tokens.color.textMuted} size={18} strokeWidth={2.2} />
                </Pressable>
                <Pressable
                  accessibilityLabel={`Eliminar peso del ${historyDateLabel(item)}`}
                  accessibilityRole="button"
                  accessibilityState={{ busy: deletingId === item.id, disabled: deletingId != null }}
                  disabled={deletingId != null}
                  hitSlop={8}
                  onPress={() => confirmDeleteWeight(item)}
                  style={({ pressed }) => [styles.rowEditAction, pressed && styles.pressed]}>
                  <Trash2 color={tokens.color.danger} size={18} strokeWidth={2.2} />
                </Pressable>
              </View>
            ) : null,
            id: item.id,
            label: historyDateLabel(item),
            secondaryValue: historyEditing ? undefined : weightVariationLabel(item, items[index + 1]),
            value: `${item.weight_kg.toFixed(1)} kg`,
          }))} />
        ) : <Text style={textStyles.muted}>Tu primera medición aparecerá aquí.</Text>}
      </Card>
      <ActionSheetModal onRequestClose={closeEdit} visible={historyFormMode != null}>
        <ActionSheetHeader icon={historyFormMode === "create" ? Plus : Pencil} onClose={closeEdit} title={historyFormMode === "create" ? "Agregar medición anterior" : "Editar peso"} />
        <ScrollView
          automaticallyAdjustKeyboardInsets={false}
          contentContainerStyle={styles.editForm}
          keyboardShouldPersistTaps="handled"
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
          style={styles.editFormScroll}>
          {historyFormMode === "create" ? <Text style={textStyles.muted}>Puedes ingresar una medición antigua que no registraste en el momento.</Text> : null}
          <NativeMeasurementField defaultValue={historyFormMode === "create" ? profile?.current_weight_kg?.toString() : undefined} kind="weight" label="Peso" onChange={setEditValue} value={editValue} />
          <NativeDateTimeField label="Fecha" maximumValue={localDateValue()} mode="date" onChange={setEditDate} value={editDate} />
          <NativeDateTimeField label="Hora (Opcional)" mode="time" onChange={setEditTime} value={editTime} />
          {editError ? <InlineNotice tone="error">{editError}</InlineNotice> : null}
          <Button bleed={false} label={historyFormMode === "create" ? "Guardar medición" : "Guardar cambios"} loading={saving} onPress={saveHistory} />
        </ScrollView>
      </ActionSheetModal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  editForm: { gap: tokens.spacing.md, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  editFormScroll: { flexGrow: 0, flexShrink: 1 },
  historyActions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  historyEditToggle: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  pressed: { opacity: 0.65 },
  rowEditAction: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  rowEditActions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  saveButtonSpacing: { marginTop: 24 - tokens.card.gap },
});
