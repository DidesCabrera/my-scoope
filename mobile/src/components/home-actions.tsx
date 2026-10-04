import { Camera, Weight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "./ui/action-sheet-modal";

type Props = {
  onCaptureLabel(): void;
  onClose(): void;
  onRegisterWeight(): void;
  visible: boolean;
};

export function HomeActions({ onCaptureLabel, onClose, onRegisterWeight, visible }: Props) {
  const navigate = (action: () => void) => {
    onClose();
    action();
  };

  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={onClose} section="home" title="Inicio" />
        <View style={styles.content}>
          <ActionSheetActions>
            <ActionSheetAction icon={Camera} label="Digitalizar etiqueta nutricional" onPress={() => navigate(onCaptureLabel)} />
            <ActionSheetAction icon={Weight} label="Registrar peso" onPress={() => navigate(onRegisterWeight)} />
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
