import { Pencil, Send, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { ShareResource } from "@/api/types";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { openNativeShare } from "@/sharing/native-share";

export function SavedComparisonActions({ canEdit = true, compact = false, name: currentName, onClose, onDelete, onEdit, onRename, onShare, visible }: { canEdit?: boolean; compact?: boolean; name: string; onClose(): void; onDelete(): Promise<void>; onEdit?(): void; onRename?(name: string): Promise<void>; onShare(): Promise<ShareResource>; visible: boolean }) {
  const [editingName, setEditingName] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [name, setName] = useState(currentName);
  const [submitting, setSubmitting] = useState(false);
  const [dismissShareImmediately, setDismissShareImmediately] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const edit = () => { onClose(); onEdit?.(); };
  const close = () => {
    if (submitting) return;
    setEditingName(false);
    setConfirmingDelete(false);
    setError(null);
    onClose();
  };
  const saveName = async () => {
    const cleanName = name.trim();
    if (!cleanName) return;
    setSubmitting(true);
    setError(null);
    try {
      await onRename?.(cleanName);
      setEditingName(false);
      onClose();
      Alert.alert("Nombre actualizado", `Ahora se llama “${cleanName}”.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };
  const remove = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onDelete();
      setConfirmingDelete(false);
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  };
  const share = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const resource = await onShare();
      setDismissShareImmediately(true);
      onClose();
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
      });
      await openNativeShare(resource);
    }
    catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setDismissShareImmediately(false);
      setSubmitting(false);
    }
  };
  return (
    <ActionSheetModal dismissImmediately={dismissShareImmediately} onRequestClose={close} visible={visible}>
      <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
        <ActionSheetHeader onClose={close} section="comparator" title={editingName ? "Editar nombre" : confirmingDelete ? "Eliminar comparación" : currentName} />
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} style={styles.scroll}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          {confirmingDelete ? <View style={styles.confirmation}>
            <Text style={styles.confirmationText}>Esta comparación se eliminará de tu lista. Los enlaces que ya compartiste conservarán su copia.</Text>
            <Button label="Eliminar comparación" loading={submitting} onPress={() => void remove()} variant="danger" />
            <Button disabled={submitting} label="Volver" onPress={() => setConfirmingDelete(false)} variant="secondary" />
          </View> : !editingName ? <ActionSheetActions>
            <ActionSheetAction disabled={submitting} icon={Send} label="Compartir" onPress={() => void share()} />
            {onRename ? <ActionSheetAction icon={Pencil} label={compact ? "Renombrar" : "Editar nombre"} onPress={() => { setName(currentName); setError(null); setEditingName(true); }} /> : null}
            {canEdit && onEdit ? <ActionSheetAction icon={Pencil} label="Editar comparación" onPress={edit} /> : null}
            <ActionSheetAction destructive disabled={submitting} icon={Trash2} label="Eliminar" onPress={() => setConfirmingDelete(true)} />
          </ActionSheetActions> : (
            <View style={styles.form}>
              <Field autoCapitalize="sentences" label="Nombre" onChangeText={(value) => setName(value.slice(0, 255))} value={name} />
              <Button disabled={!name.trim()} label="Guardar nombre" loading={submitting} onPress={() => void saveName()} />
              <Button disabled={submitting} label="Volver" onPress={() => setEditingName(false)} variant="secondary" />
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </ActionSheetModal>
  );
}

const styles = StyleSheet.create({
  confirmation: { gap: tokens.spacing.md },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  form: { gap: tokens.spacing.md },
  safeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  scroll: { flexGrow: 0, flexShrink: 1 },
});
