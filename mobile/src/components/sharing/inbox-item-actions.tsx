import { Ban, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, type EntityKind } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function InboxItemActions({
  entity,
  mode,
  onClose,
  onDelete,
  onRevoke,
  title,
  visible,
}: {
  entity: EntityKind;
  mode: "received" | "sent";
  onClose(): void;
  onDelete(): void;
  onRevoke(): void;
  title: string;
  visible: boolean;
}) {
  const [confirmingRevoke, setConfirmingRevoke] = useState(false);
  const close = () => {
    setConfirmingRevoke(false);
    onClose();
  };
  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader entity={entity} onClose={close} title={confirmingRevoke ? "Revocar acceso" : title} />
        <View style={styles.content}>
          {confirmingRevoke ? <View style={styles.confirmation}>
            <Text style={styles.confirmationText}>El enlace dejará de funcionar y ya no se podrá acceder al detalle compartido. Quienes ya guardaron una copia conservarán esa copia.</Text>
            <Button label="Confirmar revocación" onPress={onRevoke} variant="danger" />
            <Button label="Volver" onPress={() => setConfirmingRevoke(false)} variant="secondary" />
          </View> : <ActionSheetActions>
            {mode === "received" ? (
              <ActionSheetAction destructive icon={Trash2} label="Eliminar de Recibidos" onPress={onDelete} />
            ) : (
              <ActionSheetAction destructive icon={Ban} label="Revocar acceso" onPress={() => setConfirmingRevoke(true)} />
            )}
          </ActionSheetActions>}
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
});
