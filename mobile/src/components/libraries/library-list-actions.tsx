import { ListRestart, Scale, X } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

export function LibraryListActions({ canCompare, onClose, onCompare, onEdit, visible }: { canCompare: boolean; onClose(): void; onCompare(): void; onEdit(): void; visible: boolean }) {
  const actions = [
    { icon: ListRestart, label: "Editar lista", onPress: onEdit },
    ...(canCompare ? [{ icon: Scale, label: "Comparar", onPress: onCompare }] : []),
  ];
  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.sheet}>
          <View style={styles.header}><View><Text style={styles.eyebrow}>ACCIONES</Text><Text style={styles.title}>Administrar librería</Text></View><Pressable accessibilityLabel="Cerrar" onPress={onClose} style={styles.close}><X color={tokens.color.textMain} size={22} /></Pressable></View>
          <View style={styles.content}>{actions.map(({ icon: Icon, label, onPress }) => <Pressable accessibilityRole="button" key={label} onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}><View style={styles.icon}><Icon color={tokens.color.textMain} size={20} /></View><Text style={styles.label}>{label}</Text></Pressable>)}</View>
        </View>
      </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceCard }, sheet: { backgroundColor: tokens.color.surfaceCard }, header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md }, eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 }, title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", marginTop: 3 }, close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 }, content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl }, row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 }, icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 }, label: { color: tokens.color.textMain, flex: 1, fontSize: 16, fontWeight: "700" }, pressed: { opacity: 0.65 },
});
