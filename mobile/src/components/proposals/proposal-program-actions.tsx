import { ListChecks } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function ProposalProgramActions({ onClose, onOpenObjectives, visible }: { onClose(): void; onOpenObjectives(): void; visible: boolean }) {
  const openObjectives = () => { onClose(); onOpenObjectives(); };
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="proposal" title="Programa propuesto" />
        <View style={styles.content}>
          <ActionSheetActions><ActionSheetAction icon={ListChecks} label="Ver objetivos semanas" onPress={openObjectives} /></ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
