import { Pencil, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { Button } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export function PreparationCardActions({ name, onClose, onDelete, onRename, visible }: {
  name: string;
  onClose(): void;
  onDelete(): void;
  onRename(name: string): Promise<void>;
  visible: boolean;
}) {
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(name);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const close = () => { setRenaming(false); setError(null); onClose(); };
  const save = async () => {
    if (!nameDraft.trim()) { setError("Escribe un nombre para la preparación."); return; }
    setSubmitting(true); setError(null);
    try { await onRename(nameDraft.trim()); close(); }
    catch (failure) { setError(userFacingError(failure)); }
    finally { setSubmitting(false); }
  };

  return <ActionSheetModal onRequestClose={close} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
      <ActionSheetHeader entity="preparation" onClose={close} title={renaming ? "Renombrar preparación" : name} />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {renaming ? <View style={styles.form}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          <Field autoCapitalize="sentences" label="Nombre" onChangeText={setNameDraft} value={nameDraft} />
          <Button disabled={!nameDraft.trim() || submitting} label="Guardar nombre" loading={submitting} onPress={() => void save()} />
          <Button label="Volver" onPress={() => setRenaming(false)} variant="secondary" />
        </View> : <ActionSheetActions>
          <ActionSheetAction icon={Pencil} label="Renombrar preparación" onPress={() => { setNameDraft(name); setError(null); setRenaming(true); }} />
          <ActionSheetAction destructive icon={Trash2} label="Eliminar preparación" onPress={() => { close(); onDelete(); }} />
        </ActionSheetActions>}
      </ScrollView>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  form: { gap: tokens.spacing.md },
});
