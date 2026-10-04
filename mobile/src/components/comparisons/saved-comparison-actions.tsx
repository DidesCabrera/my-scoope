import { Pencil } from "lucide-react-native";
import { useState } from "react";
import { Alert, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export function SavedComparisonActions({ name: currentName, onClose, onEdit, onRename, visible }: { name: string; onClose(): void; onEdit(): void; onRename(name: string): Promise<void>; visible: boolean }) {
  const [editingName, setEditingName] = useState(false);
  const [name, setName] = useState(currentName);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const edit = () => { onClose(); onEdit(); };
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
        <ActionSheetHeader onClose={close} section="comparator" title={editingName ? "Editar nombre" : "Comparación"} />
        <View style={styles.content}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          {!editingName ? <ActionSheetActions>
            <ActionSheetAction icon={Pencil} label="Editar nombre" onPress={() => { setName(currentName); setError(null); setEditingName(true); }} />
            <ActionSheetAction icon={Pencil} label="Editar comparación" onPress={edit} />
          </ActionSheetActions> : (
            <View style={styles.form}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => setName(value.slice(0, 255))} value={name} />
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
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  form: { gap: tokens.spacing.md },
  safeArea: { backgroundColor: tokens.color.surfaceCard },
});
