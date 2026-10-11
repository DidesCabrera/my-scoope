import { CalendarClock, Clock3, Info, Pencil } from "lucide-react-native";
import { useState } from "react";
import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { NativeDateTimeField } from "@/components/ui/native-date-time-field";
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
      <NativeDateTimeField
        label="Hora de la comida"
        minuteInterval={5}
        mode="time"
        onChange={(value) => setHour(value)}
        value={hour}
      />
      <Button disabled={!TIME_PATTERN.test(hour)} label="Guardar hora" loading={submitting} onPress={() => void save()} />
      <Button disabled={submitting} label="Cancelar" onPress={onCancel} variant="secondary" />
    </View>
  );
}

type CalendarizedEntityActionsProps = {
  entityName: string;
  initialAction?: Exclude<SelectedAction, null>;
  onOpenInformation?: () => void;
  onVisibleChange(visible: boolean): void;
  rename?: {
    onSubmit(name: string): Promise<void>;
  };
  timeChange?: {
    initialTime?: string | null;
    onSubmit(hour: string): Promise<void>;
  };
  timeChangeInMenu?: boolean;
  visible: boolean;
};

type SelectedAction = "rename" | "change-time" | null;

export function CalendarizedEntityActions({ entityName, initialAction, onOpenInformation, onVisibleChange, rename, timeChange, timeChangeInMenu = true, visible }: CalendarizedEntityActionsProps) {
  const [selected, setSelected] = useState<SelectedAction>(initialAction ?? null);
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
        <ActionSheetHeader icon={CalendarClock} onClose={close} title={title} />
        <ScrollView
          automaticallyAdjustKeyboardInsets
          contentContainerStyle={styles.sheetContent}
          keyboardShouldPersistTaps="handled"
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
          style={styles.sheetScroll}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          {!selected ? <ActionSheetActions>
            {onOpenInformation ? <ActionSheetAction icon={Info} label="Ver información del elemento" onPress={() => { onVisibleChange(false); onOpenInformation(); }} /> : null}
            {rename ? <ActionSheetAction icon={Pencil} label="Renombrar" onPress={() => { setName(entityName); setError(null); setSelected("rename"); }} /> : null}
            {timeChange && timeChangeInMenu ? <ActionSheetAction icon={Clock3} label="Cambiar hora" onPress={() => setSelected("change-time")} /> : null}
          </ActionSheetActions> : null}
          {selected === "rename" && rename ? (
            <View style={styles.form}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => setName(value.slice(0, 255))} value={name} />
              <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void saveName()} />
              <Button disabled={submitting} label="Volver" onPress={() => setSelected(null)} variant="secondary" />
            </View>
          ) : null}
          {selected === "change-time" && timeChange ? (
            <MealTimeForm initialTime={timeChange.initialTime} onCancel={initialAction ? close : () => setSelected(null)} onSaved={close} onSubmit={timeChange.onSubmit} />
          ) : null}
        </ScrollView>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetScroll: { flexGrow: 0, flexShrink: 1 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  form: { gap: tokens.spacing.md },
});
