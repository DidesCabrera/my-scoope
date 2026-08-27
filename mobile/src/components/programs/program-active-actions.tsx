import { Bell, History, Pause, Play, RefreshCw, Trash2, X } from "lucide-react-native";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarizationStatus } from "@/api/types";
import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

type ProgramStateAction = "pause" | "resume" | "cancel";
type ConfirmableAction = Extract<ProgramStateAction, "pause" | "cancel">;

type ProgramActiveActionsProps = {
  onChangeProgram(): void;
  onClose(): void;
  onOpenHistory(): void;
  onOpenReminders(): void;
  onStateAction(action: ProgramStateAction): Promise<void>;
  status: CalendarizationStatus | null;
  visible: boolean;
};

const confirmationCopy: Record<ConfirmableAction, { confirmLabel: string; message: string; title: string }> = {
  pause: {
    confirmLabel: "Pausar",
    message: "Tu progreso se conservará y podrás reanudar este programa más adelante.",
    title: "¿Pausar el programa?",
  },
  cancel: {
    confirmLabel: "Cancelar programa",
    message: "El programa saldrá de tu recorrido actual y quedará disponible en el historial.",
    title: "¿Cancelar este programa?",
  },
};

export function ProgramActiveActions({
  onChangeProgram,
  onClose,
  onOpenHistory,
  onOpenReminders,
  onStateAction,
  status,
  visible,
}: ProgramActiveActionsProps) {
  const [selected, setSelected] = useState<ConfirmableAction | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (submitting) return;
    setSelected(null);
    setError(null);
    onClose();
  };

  const navigate = (callback: () => void) => {
    setSelected(null);
    setError(null);
    onClose();
    callback();
  };

  const execute = async (action: ProgramStateAction) => {
    setSubmitting(true);
    setError(null);
    try {
      await onStateAction(action);
      setSelected(null);
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };

  const confirmation = selected ? confirmationCopy[selected] : null;

  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <View style={styles.headerCopy}>
              <Text style={styles.eyebrow}>ACCIONES</Text>
              <Text numberOfLines={1} style={styles.title}>{confirmation?.title ?? "Programa en curso"}</Text>
            </View>
            <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.close, pressed && styles.pressed]}>
              <X color={tokens.color.textMain} size={22} />
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}

            {confirmation && selected ? (
              <View style={styles.confirmation}>
                <Text style={styles.confirmationText}>{confirmation.message}</Text>
                <Button
                  label={confirmation.confirmLabel}
                  loading={submitting}
                  onPress={() => void execute(selected)}
                  variant={selected === "cancel" ? "danger" : "primary"}
                />
                <Button disabled={submitting} label="Volver" onPress={() => setSelected(null)} variant="secondary" />
              </View>
            ) : (
              <View>
                {status ? (
                  <>
                    {status === "paused" ? (
                      <ActionRow icon={Play} label="Reanudar programa" onPress={() => void execute("resume")} />
                    ) : (
                      <ActionRow icon={Pause} label="Pausar programa" onPress={() => setSelected("pause")} />
                    )}
                    <ActionRow icon={Bell} label="Configurar recordatorios" onPress={() => navigate(onOpenReminders)} />
                    <ActionRow destructive icon={Trash2} label="Cancelar programa" onPress={() => setSelected("cancel")} />
                  </>
                ) : null}
                <ActionRow icon={RefreshCw} label="Cambiar de programa" onPress={() => navigate(onChangeProgram)} />
                <ActionRow icon={History} label="Historial de programas" onPress={() => navigate(onOpenHistory)} />
              </View>
            )}
          </ScrollView>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

function ActionRow({ destructive = false, icon: Icon, label, onPress }: { destructive?: boolean; icon: typeof Pause; label: string; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View style={styles.icon}>
        <Icon color={destructive ? tokens.color.danger : tokens.color.textMain} size={20} />
      </View>
      <Text style={[styles.label, destructive && styles.danger]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard, maxHeight: "88%" },
  sheet: { backgroundColor: tokens.color.surfaceCard },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" },
  danger: { color: tokens.color.danger },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  pressed: { opacity: 0.65 },
});
