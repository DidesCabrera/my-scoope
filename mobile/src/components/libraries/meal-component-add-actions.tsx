import { Carrot, CookingPot } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function MealComponentAddActions({ onClose, onFood, onPreparation, visible }: { onClose(): void; onFood(): void; onPreparation(): void; visible: boolean }) {
  const select = (action: () => void) => {
    onClose();
    action();
  };

  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <View style={styles.sheet}>
        <ActionSheetHeader entity="meal" onClose={onClose} title="Agregar a la comida" />
        <View style={styles.content}>
          <ActionSheetActions>
            <ActionSheetAction icon={Carrot} iconColor={tokens.color.food} label="Agregar alimento" onPress={() => select(onFood)} />
            <ActionSheetAction icon={CookingPot} iconColor={tokens.color.preparation} label="Agregar preparación" onPress={() => select(onPreparation)} />
          </ActionSheetActions>
        </View>
      </View>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  sheet: { backgroundColor: tokens.color.surfaceCard },
});
