import { Info, X } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function SharedResourceActions({ onOpenInformation, onVisibleChange, title, visible }: { onOpenInformation(): void; onVisibleChange(visible: boolean): void; title: string; visible: boolean }) {
  const close = () => onVisibleChange(false);
  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>ACCIONES</Text>
            <Text numberOfLines={1} style={styles.title}>{title}</Text>
          </View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.close, pressed && styles.pressed]}>
            <X color={tokens.color.textMain} size={22} />
          </Pressable>
        </View>
        <View style={styles.content}>
          <Pressable accessibilityRole="button" onPress={() => { close(); onOpenInformation(); }} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
            <View style={styles.icon}><Info color={tokens.color.textMain} size={20} /></View>
            <Text style={styles.label}>Ver información del elemento</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" },
  pressed: { opacity: 0.65 },
});
