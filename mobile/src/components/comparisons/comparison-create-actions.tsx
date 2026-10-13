import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { ComparisonKind } from "@/api/types";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { EntityIcon } from "@/components/ui/product";
import { tokens } from "@/design/tokens";

type Props = {
  onClose(): void;
  onSelect(kind: ComparisonKind): void;
  visible: boolean;
};

export function ComparisonCreateActions({ onClose, onSelect, visible }: Props) {
  const select = (kind: ComparisonKind) => {
    onClose();
    onSelect(kind);
  };

  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="comparator" title="Nueva comparación" />
        <View style={styles.content}>
          <ActionSheetActions>
            <ActionSheetAction iconNode={<EntityIcon entity="food" size="compact" />} label="Comparar alimentos" onPress={() => select("foods")} />
            <ActionSheetAction iconNode={<EntityIcon entity="meal" size="compact" />} label="Comparar comidas" onPress={() => select("meals")} />
            <ActionSheetAction iconNode={<EntityIcon entity="dailyPlan" size="compact" />} label="Comparar planes diarios" onPress={() => select("dailyplans")} />
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
