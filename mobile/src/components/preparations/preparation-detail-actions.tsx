import { useState } from "react";
import { Info, Pencil, Scale, Settings2, Trash2 } from "lucide-react-native";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import { Button } from "@/components/ui";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Field, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type AdvancedOptions = { estimatedYieldG: number; manualYield: boolean; yieldG: number; portionG: number };

type PreparationDetailActionsProps = {
  advanced?: AdvancedOptions;
  inMeal: boolean;
  isActive: boolean;
  isPersonal: boolean;
  name: string;
  onClose(): void;
  onEditMealPortion(): void;
  onOpenInformation(): void;
  onRemoveFromMeal(): void;
  onRemovePersonal(): void;
  onRename(name: string): Promise<void>;
  onSaveAdvanced(options: { manualYield: boolean; yieldG: number; portionG: number }): Promise<void>;
  visible: boolean;
};

export function PreparationDetailActions({ advanced, inMeal, isActive, isPersonal, name, onClose, onEditMealPortion, onOpenInformation, onRemoveFromMeal, onRemovePersonal, onRename, onSaveAdvanced, visible }: PreparationDetailActionsProps) {
  const [selected, setSelected] = useState<"rename" | "advanced" | null>(null);
  const [nameDraft, setNameDraft] = useState(name);
  const [manualYield, setManualYield] = useState(false);
  const [yieldDraft, setYieldDraft] = useState("");
  const [portionDraft, setPortionDraft] = useState("100");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const close = () => { setSelected(null); setError(null); onClose(); };
  const select = (action: () => void) => { close(); action(); };
  const openRename = () => { setNameDraft(name); setError(null); setSelected("rename"); };
  const openAdvanced = () => {
    if (!advanced) return;
    setManualYield(advanced.manualYield);
    setYieldDraft(String(advanced.yieldG));
    setPortionDraft(String(advanced.portionG));
    setError(null);
    setSelected("advanced");
  };
  const saveName = async () => {
    if (!nameDraft.trim()) { setError("Escribe un nombre para la preparación."); return; }
    setSubmitting(true); setError(null);
    try { await onRename(nameDraft.trim()); close(); }
    catch (failure) { setError(userFacingError(failure)); }
    finally { setSubmitting(false); }
  };
  const saveAdvanced = async () => {
    const yieldG = Number(yieldDraft.trim().replace(",", "."));
    const portionG = Number(portionDraft.trim().replace(",", "."));
    if ((manualYield && (!Number.isFinite(yieldG) || yieldG <= 0)) || !Number.isFinite(portionG) || portionG <= 0) {
      setError("Define un rendimiento y una porción válidos en gramos."); return;
    }
    setSubmitting(true); setError(null);
    try { await onSaveAdvanced({ manualYield, yieldG, portionG }); close(); }
    catch (failure) { setError(userFacingError(failure)); }
    finally { setSubmitting(false); }
  };

  return <ActionSheetModal onRequestClose={close} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
      <ActionSheetHeader entity="preparation" onClose={close} title={selected === "rename" ? "Renombrar preparación" : selected === "advanced" ? "Opciones avanzadas" : name} />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {selected === null ? <ActionSheetActions>
          <ActionSheetAction icon={Info} label="Ver información del elemento" onPress={() => select(onOpenInformation)} />
          {isPersonal && isActive ? <ActionSheetAction icon={Pencil} label="Renombrar" onPress={openRename} /> : null}
          {isPersonal && isActive && advanced ? <ActionSheetAction icon={Settings2} label="Configurar opciones avanzadas" onPress={openAdvanced} /> : null}
          {inMeal && isActive ? <ActionSheetAction icon={Scale} label="Editar porción en esta comida" onPress={() => select(onEditMealPortion)} /> : null}
          {inMeal ? <ActionSheetAction destructive icon={Trash2} label="Quitar de esta comida" onPress={() => select(onRemoveFromMeal)} /> : null}
          {isPersonal && isActive ? <ActionSheetAction destructive icon={Trash2} label="Eliminar preparación" onPress={() => select(onRemovePersonal)} /> : null}
        </ActionSheetActions> : null}
        {selected === "rename" ? <View style={styles.form}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          <Field autoCapitalize="sentences" label="Nombre" onChangeText={setNameDraft} value={nameDraft} />
          <Button disabled={!nameDraft.trim()} label="Guardar nombre" loading={submitting} onPress={() => void saveName()} />
          <Button label="Volver" onPress={() => setSelected(null)} variant="secondary" />
        </View> : null}
        {selected === "advanced" && advanced ? <View style={styles.form}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          <Text style={styles.helper}>Rendimiento estimado: {advanced.estimatedYieldG} g, según los alimentos de la receta.</Text>
          <Button label={manualYield ? "Usar rendimiento estimado" : "Corregir rendimiento final"} onPress={() => setManualYield((current) => !current)} variant="secondary" />
          {manualYield ? <Field keyboardType="decimal-pad" label="Rendimiento final (g)" onChangeText={setYieldDraft} value={yieldDraft} /> : null}
          <Field keyboardType="decimal-pad" label="Porción habitual (g)" onChangeText={setPortionDraft} value={portionDraft} />
          <Button label="Guardar opciones" loading={submitting} onPress={() => void saveAdvanced()} />
          <Button label="Volver" onPress={() => setSelected(null)} variant="secondary" />
        </View> : null}
      </ScrollView>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  content: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  form: { gap: tokens.spacing.md },
  helper: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 20 },
});
