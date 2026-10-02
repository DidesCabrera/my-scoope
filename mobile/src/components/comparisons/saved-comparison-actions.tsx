import { Pencil, X } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function SavedComparisonActions({ onClose, onEdit, visible }: { onClose(): void; onEdit(): void; visible: boolean }) {
  const edit = () => { onClose(); onEdit(); };
  return (
    <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.header}>
          <View><Text style={styles.eyebrow}>ACCIONES</Text><Text style={styles.title}>Comparación</Text></View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={onClose} style={({ pressed }) => [styles.close, pressed && styles.pressed]}><X color={tokens.color.textMain} size={22} /></Pressable>
        </View>
        <View style={styles.content}>
          <Pressable accessibilityRole="button" onPress={edit} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
            <View style={styles.icon}><Pencil color={tokens.color.textMain} size={20} /></View>
            <Text style={styles.label}>Editar comparación</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold, marginTop: 3 },
});
