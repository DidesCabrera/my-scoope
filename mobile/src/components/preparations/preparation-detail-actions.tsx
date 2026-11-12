import { Info, Pencil, Scale, Trash2 } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

type PreparationDetailActionsProps = {
  inMeal: boolean;
  isActive: boolean;
  isPersonal: boolean;
  name: string;
  onClose(): void;
  onEdit(): void;
  onEditMealPortion(): void;
  onOpenInformation(): void;
  onRemoveFromMeal(): void;
  onRemovePersonal(): void;
  visible: boolean;
};

export function PreparationDetailActions({ inMeal, isActive, isPersonal, name, onClose, onEdit, onEditMealPortion, onOpenInformation, onRemoveFromMeal, onRemovePersonal, visible }: PreparationDetailActionsProps) {
  const select = (action: () => void) => {
    onClose();
    action();
  };

  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
      <ActionSheetHeader entity="preparation" onClose={onClose} title={name} />
      <View style={styles.content}>
        <ActionSheetActions>
          <ActionSheetAction icon={Info} label="Ver información del elemento" onPress={() => select(onOpenInformation)} />
          {isPersonal && isActive ? <ActionSheetAction icon={Pencil} label="Editar preparación" onPress={() => select(onEdit)} /> : null}
          {inMeal && isActive ? <ActionSheetAction icon={Scale} label="Editar porción en esta comida" onPress={() => select(onEditMealPortion)} /> : null}
          {inMeal ? <ActionSheetAction destructive icon={Trash2} label="Quitar de esta comida" onPress={() => select(onRemoveFromMeal)} /> : null}
          {isPersonal && isActive ? <ActionSheetAction destructive icon={Trash2} label="Eliminar preparación" onPress={() => select(onRemovePersonal)} /> : null}
        </ActionSheetActions>
      </View>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
