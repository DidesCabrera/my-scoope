import { ClipboardCheck, Pencil, X } from "lucide-react-native";
import { useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export function AssistantChatActions({ currentName, onClose, onOpenProposals, onRename, visible }: { currentName: string; onClose(): void; onOpenProposals(): void; onRename(name: string): Promise<void>; visible: boolean }) {
  const [editingName, setEditingName] = useState(false);
  const [name, setName] = useState(currentName);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const openProposals = () => { onClose(); onOpenProposals(); };
  const close = () => {
    if (submitting) return;
    setEditingName(false);
    setError(null);
    onClose();
  };
  const saveName = async () => {
    const cleanName = name.trim();
    if (!cleanName) return;
    setSubmitting(true);
    setError(null);
    try {
      await onRename(cleanName);
      setEditingName(false);
      onClose();
      Alert.alert("Nombre actualizado", `Ahora se llama “${cleanName}”.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };
  return (
    <ActionSheetModal onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <View style={styles.header}>
          <View><Text style={styles.eyebrow}>{editingName ? "NOMBRE" : "ACCIONES"}</Text><Text style={styles.title}>{editingName ? "Editar nombre" : "Chat"}</Text></View>
          <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={close} style={({ pressed }) => [styles.close, pressed && styles.pressed]}><X color={tokens.color.textMain} size={22} /></Pressable>
        </View>
        <View style={styles.content}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          {!editingName ? <>
            <Pressable accessibilityRole="button" onPress={() => { setName(currentName); setError(null); setEditingName(true); }} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
              <View style={styles.icon}><Pencil color={tokens.color.textMain} size={20} /></View>
              <Text style={styles.label}>Editar nombre</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={openProposals} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
              <View style={styles.icon}><ClipboardCheck color={tokens.color.textMain} size={20} /></View>
              <Text style={styles.label}>Ver propuestas del chat</Text>
            </Pressable>
          </> : (
            <View style={styles.form}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => setName(value.slice(0, 140))} value={name} />
              <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void saveName()} />
              <Button disabled={submitting} label="Volver" onPress={() => setEditingName(false)} variant="secondary" />
            </View>
          )}
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  form: { gap: tokens.spacing.md },
  header: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58 },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold, marginTop: 3 },
});
