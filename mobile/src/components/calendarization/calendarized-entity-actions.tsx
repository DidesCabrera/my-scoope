import { Clock3, Pencil, X } from "lucide-react-native";
import { useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type MealTimeFormProps = {
  initialTime?: string | null;
  onCancel(): void;
  onSaved?(): void;
  onSubmit(hour: string): Promise<void>;
};

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

export function MealTimeForm({ initialTime, onCancel, onSaved, onSubmit }: MealTimeFormProps) {
  const [hour, setHour] = useState(initialTime?.slice(0, 5) ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (!TIME_PATTERN.test(hour)) {
      setError("Ingresa una hora válida en formato HH:MM.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(hour);
      (onSaved ?? onCancel)();
      Alert.alert("Hora actualizada", `Esta comida quedó programada a las ${hour}.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.form}>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <Field
        autoCapitalize="none"
        keyboardType="numbers-and-punctuation"
        label="Hora de la comida"
        onChangeText={(value) => setHour(value.slice(0, 5))}
        placeholder="08:00"
        value={hour}
      />
      <Text style={styles.help}>Usa el formato de 24 horas, por ejemplo 08:00 o 20:30.</Text>
      <Button disabled={!TIME_PATTERN.test(hour)} label="Guardar hora" loading={submitting} onPress={() => void save()} />
      <Button disabled={submitting} label="Cancelar" onPress={onCancel} variant="secondary" />
    </View>
  );
}

type CalendarizedEntityActionsProps = {
  entityName: string;
  onVisibleChange(visible: boolean): void;
  rename?: {
    onSubmit(name: string): Promise<void>;
  };
  timeChange?: {
    initialTime?: string | null;
    onSubmit(hour: string): Promise<void>;
  };
  visible: boolean;
};

type SelectedAction = "rename" | "change-time" | null;

export function CalendarizedEntityActions({ entityName, onVisibleChange, rename, timeChange, visible }: CalendarizedEntityActionsProps) {
  const [selected, setSelected] = useState<SelectedAction>(null);
  const [name, setName] = useState(entityName);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (submitting) return;
    setSelected(null);
    setError(null);
    onVisibleChange(false);
  };

  const saveName = async () => {
    const cleanName = name.trim();
    if (!cleanName) return;
    setSubmitting(true);
    setError(null);
    try {
      await rename?.onSubmit(cleanName);
      setSubmitting(false);
      setSelected(null);
      onVisibleChange(false);
      Alert.alert("Nombre actualizado", `Ahora se llama “${cleanName}”.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const title = selected === "rename" ? "Renombrar" : selected === "change-time" ? "Cambiar hora" : entityName;

  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
        <View style={styles.sheetHeader}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>{selected === "change-time" ? "HORARIO" : selected === "rename" ? "NOMBRE" : "ACCIONES"}</Text>
            <Text numberOfLines={1} style={styles.title}>{title}</Text>
          </View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
            <X color={tokens.color.textMain} size={22} />
          </Pressable>
        </View>
        <View style={styles.sheetContent}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          {!selected && rename ? (
            <Pressable accessibilityRole="button" onPress={() => { setName(entityName); setError(null); setSelected("rename"); }} style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}>
              <View style={styles.actionIcon}><Pencil color={tokens.color.textMain} size={20} /></View>
              <Text style={styles.actionLabel}>Renombrar</Text>
            </Pressable>
          ) : null}
          {!selected && timeChange ? (
            <Pressable accessibilityRole="button" onPress={() => setSelected("change-time")} style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}>
              <View style={styles.actionIcon}><Clock3 color={tokens.color.textMain} size={20} /></View>
              <Text style={styles.actionLabel}>Cambiar hora</Text>
            </Pressable>
          ) : null}
          {selected === "rename" && rename ? (
            <View style={styles.form}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => setName(value.slice(0, 255))} value={name} />
              <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void saveName()} />
              <Button disabled={submitting} label="Volver" onPress={() => setSelected(null)} variant="secondary" />
            </View>
          ) : null}
          {selected === "change-time" && timeChange ? (
            <MealTimeForm initialTime={timeChange.initialTime} onCancel={() => setSelected(null)} onSaved={close} onSubmit={timeChange.onSubmit} />
          ) : null}
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  sheetHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  closeButton: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingVertical: tokens.spacing.sm },
  actionIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" },
  form: { gap: tokens.spacing.md },
  help: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  pressed: { opacity: 0.65 },
});
