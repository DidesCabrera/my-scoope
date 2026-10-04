import { ClipboardCheck } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function ProposalDetailActions({ onClose, onReviewFacts, visible }: { onClose(): void; onReviewFacts(): void; visible: boolean }) {
  const reviewFacts = () => { onClose(); onReviewFacts(); };
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="proposal" title="Propuesta" />
        <View style={styles.content}>
          <ActionSheetActions><ActionSheetAction icon={ClipboardCheck} label="Revisar fichas de la propuesta" onPress={reviewFacts} /></ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
