import { Camera, Weight, X } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";
import { ActionSheetModal } from "./ui/action-sheet-modal";

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
        <View style={styles.header}>
          <View>
            <Text style={styles.eyebrow}>ACCIONES</Text>
            <Text style={styles.title}>Inicio</Text>
          </View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={onClose} style={({ pressed }) => [styles.close, pressed && styles.pressed]}>
            <X color={tokens.color.textMain} size={22} />
          </Pressable>
        </View>
        <View style={styles.content}>
          <ActionRow icon={Camera} label="Digitalizar etiqueta nutricional" onPress={() => navigate(onCaptureLabel)} />
          <ActionRow icon={Weight} label="Registrar peso" onPress={() => navigate(onRegisterWeight)} />
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

function ActionRow({ icon: Icon, label, onPress }: { icon: typeof Camera; label: string; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View style={styles.icon}><Icon color={tokens.color.textMain} size={20} /></View>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.extraBold, letterSpacing: 1.1 },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold, marginTop: 3 },
});
