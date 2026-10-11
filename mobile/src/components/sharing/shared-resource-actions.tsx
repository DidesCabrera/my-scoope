import { Info, Share2 } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function SharedResourceActions({ onOpenInformation, onVisibleChange, title, visible }: { onOpenInformation(): void; onVisibleChange(visible: boolean): void; title: string; visible: boolean }) {
  const close = () => onVisibleChange(false);
  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader icon={Share2} onClose={close} title={title} />
        <View style={styles.content}>
          <ActionSheetActions><ActionSheetAction icon={Info} label="Ver información del elemento" onPress={() => { close(); onOpenInformation(); }} /></ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
