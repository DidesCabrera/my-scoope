import { ListRestart } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

type Props = {
  onClose(): void;
  onEdit(): void;
  section: "chats" | "proposals";
  visible: boolean;
};

export function AssistantListActions({ onClose, onEdit, section, visible }: Props) {
  const editList = () => {
    onClose();
    onEdit();
  };
  const title = section === "chats" ? "Chats" : "Propuestas";
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="chat" title={`Administrar ${title.toLowerCase()}`} />
        <View style={styles.content}>
          <ActionSheetActions>
            <ActionSheetAction icon={ListRestart} label="Editar lista" onPress={editList} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
