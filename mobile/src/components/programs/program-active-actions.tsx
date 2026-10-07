import { Bell, ExternalLink, History, Info, Pause, Play, RefreshCw, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarizationStatus } from "@/api/types";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

type ProgramStateAction = "pause" | "resume" | "cancel";
type ConfirmableAction = Extract<ProgramStateAction, "pause" | "cancel">;

type ProgramActiveActionsProps = {
  onChangeProgram(): void;
  onClose(): void;
  onOpenInformation(): void;
  onOpenHistory(): void;
  onOpenOriginalProgram?: () => void;
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
  onOpenInformation,
  onOpenHistory,
  onOpenOriginalProgram,
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
          <ActionSheetHeader entity="program" onClose={close} title={confirmation?.title ?? "Programa en curso"} />

          <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" nestedScrollEnabled showsVerticalScrollIndicator={false} style={styles.sheetScroll}>
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
              <ActionSheetActions>
                <ActionSheetAction icon={Info} label="Ver información del elemento" onPress={() => navigate(onOpenInformation)} />
                {status ? (
                  <>
                    {status === "paused" ? (
                      <ActionSheetAction icon={Play} label="Reanudar programa" onPress={() => void execute("resume")} />
                    ) : (
                      <ActionSheetAction icon={Pause} label="Pausar programa" onPress={() => setSelected("pause")} />
                    )}
                    <ActionSheetAction icon={Bell} label="Configurar recordatorios" onPress={() => navigate(onOpenReminders)} />
                    <ActionSheetAction destructive icon={Trash2} label="Cancelar programa" onPress={() => setSelected("cancel")} />
                  </>
                ) : null}
                {onOpenOriginalProgram ? <ActionSheetAction icon={ExternalLink} label="Ver programa original" onPress={() => navigate(onOpenOriginalProgram)} /> : null}
                <ActionSheetAction icon={RefreshCw} label="Cambiar de programa" onPress={() => navigate(onChangeProgram)} />
                <ActionSheetAction icon={History} label="Historial de programas" onPress={() => navigate(onOpenHistory)} />
              </ActionSheetActions>
            )}
          </ScrollView>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard, maxHeight: "88%" },
  sheet: { backgroundColor: tokens.color.surfaceCard },
  sheetScroll: { flexGrow: 0, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
});
