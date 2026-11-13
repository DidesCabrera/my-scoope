import { Pencil, Trash2 } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function SupplementActionsSheet({ name, onClose, onDelete, onEdit, visible }: { name: string; onClose(): void; onDelete(): void; onEdit(): void; visible: boolean }) {
  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <ActionSheetHeader entity="supplement" onClose={onClose} title={name} />
      <View style={styles.content}>
        <ActionSheetActions>
          <ActionSheetAction icon={Pencil} label="Editar suplemento" onPress={onEdit} />
          <ActionSheetAction destructive icon={Trash2} label="Eliminar suplemento" onPress={onDelete} />
        </ActionSheetActions>
      </View>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
