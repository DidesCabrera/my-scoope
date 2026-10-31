import { Camera, PencilLine } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function FoodAddActions({ onClose, onManualAdd, onScanLabel, visible }: { onClose(): void; onManualAdd(): void; onScanLabel(): void; visible: boolean }) {
  const navigate = (action: () => void) => {
    onClose();
    action();
  };

  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.sheet}>
          <ActionSheetHeader entity="food" onClose={onClose} title="Agregar alimento" />
          <View style={styles.content}>
            <ActionSheetActions>
              <ActionSheetAction icon={PencilLine} label="Agregar manualmente" onPress={() => navigate(onManualAdd)} />
              <ActionSheetAction icon={Camera} label="Digitalizar etiqueta" onPress={() => navigate(onScanLabel)} />
            </ActionSheetActions>
          </View>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  sheet: { backgroundColor: tokens.color.surfaceCard },
});
