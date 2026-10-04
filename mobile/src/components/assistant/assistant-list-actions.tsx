import { Plus } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

type Props = {
  onClose(): void;
  onNewChat?(): void;
  visible: boolean;
};

export function AssistantListActions({ onClose, onNewChat, visible }: Props) {
  const startChat = () => {
    onClose();
    onNewChat?.();
  };
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="chat" title="Chats" />
        <View style={styles.content}>
          <ActionSheetActions><ActionSheetAction icon={Plus} label="Nuevo chat" onPress={startChat} /></ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
