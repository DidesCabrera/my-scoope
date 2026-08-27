import { ArrowUpDown, Scale, Trash2, X } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function LibraryListActions({ canCompare, onClose, onCompare, onDelete, onReorder, visible }: { canCompare: boolean; onClose(): void; onCompare(): void; onDelete(): void; onReorder(): void; visible: boolean }) {
  const actions = [
    { icon: ArrowUpDown, label: "Reordenar", onPress: onReorder },
    ...(canCompare ? [{ icon: Scale, label: "Comparar", onPress: onCompare }] : []),
    { destructive: true, icon: Trash2, label: "Eliminar", onPress: onDelete },
  ];
  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.sheet}>
          <View style={styles.header}><View><Text style={styles.eyebrow}>ACCIONES</Text><Text style={styles.title}>Administrar librería</Text></View><Pressable accessibilityLabel="Cerrar" onPress={onClose} style={styles.close}><X color={tokens.color.textMain} size={22} /></Pressable></View>
          <View style={styles.content}>{actions.map(({ destructive, icon: Icon, label, onPress }) => <Pressable accessibilityRole="button" key={label} onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}><View style={styles.icon}><Icon color={destructive ? tokens.color.danger : tokens.color.textMain} size={20} /></View><Text style={[styles.label, destructive && styles.danger]}>{label}</Text></Pressable>)}</View>
        </View>
      </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard }, sheet: { backgroundColor: tokens.color.surfaceCard }, header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md }, eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1 }, title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", marginTop: 3 }, close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 }, content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl }, row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 }, icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 }, label: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" }, danger: { color: tokens.color.danger }, pressed: { opacity: 0.65 },
});
