import { Pencil, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ComparisonPanelGestureRows, StaticComparisonPanelRows } from "@/components/libraries/comparison-panel-gesture-rows";
import { PanelSurface } from "@/components/panels";
import { Button, EntityIcon, InlineNotice } from "@/components/ui";
import { ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Field } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { runGuardedNavigation } from "@/navigation/navigation-press-guard";

export type SupplementIntakeTableItem = {
  brand?: string | null;
  id: string;
  name: string;
  quantity: string;
  unit: string;
};

const unitLabels: Record<string, { plural?: string; singular: string }> = {
  capsule: { plural: "cápsulas", singular: "cápsula" },
  drop: { plural: "gotas", singular: "gota" },
  g: { singular: "g" },
  gummy: { plural: "gomitas", singular: "gomita" },
  iu: { singular: "UI" },
  mcg: { singular: "mcg" },
  mg: { singular: "mg" },
  ml: { singular: "ml" },
  sachet: { plural: "sobres", singular: "sobre" },
  scoop: { plural: "medidas", singular: "medida" },
  softgel: { plural: "cápsulas blandas", singular: "cápsula blanda" },
  tablet: { plural: "comprimidos", singular: "comprimido" },
  tsp: { plural: "cucharaditas", singular: "cucharadita" },
};

function unitLabel(quantityValue: string, unitValue: string) {
  const quantity = Number(quantityValue);
  const labels = unitLabels[unitValue];
  if (!labels) return unitValue;
  return quantity === 1 ? labels.singular : labels.plural ?? labels.singular;
}

function doseLabel(quantityValue: string, unitValue: string) {
  const quantity = Number(quantityValue);
  const formatted = Number.isFinite(quantity)
    ? quantity.toLocaleString("es-CL", { maximumFractionDigits: 3 })
    : quantityValue;
  return `${formatted} ${unitLabel(quantityValue, unitValue)}`;
}

export function SupplementIntakeItemsTable({ editable = true, items, onOpen, onQuantityChange, onRemove, onReorder }: {
  editable?: boolean;
  items: SupplementIntakeTableItem[];
  onOpen(item: SupplementIntakeTableItem): void;
  onQuantityChange?(item: SupplementIntakeTableItem, quantity: string): void;
  onRemove?(item: SupplementIntakeTableItem): void;
  onReorder?(items: SupplementIntakeTableItem[]): void;
}) {
  const [editingItem, setEditingItem] = useState<SupplementIntakeTableItem | null>(null);
  const [quantity, setQuantity] = useState("");
  const [doseError, setDoseError] = useState<string | null>(null);
  const closeDoseEditor = () => { setEditingItem(null); setQuantity(""); setDoseError(null); };
  const openDoseEditor = (item: SupplementIntakeTableItem) => { setEditingItem(item); setQuantity(item.quantity); setDoseError(null); };
  const saveDose = () => {
    if (!editingItem) return;
    const normalizedQuantity = quantity.trim().replace(",", ".");
    if (!(Number(normalizedQuantity) > 0)) { setDoseError("Escribe una cantidad válida."); return; }
    onQuantityChange?.(editingItem, normalizedQuantity);
    closeDoseEditor();
  };
  const renderRow = (item: SupplementIntakeTableItem, index: number) => <View style={[styles.row, styles.itemRow, index === items.length - 1 && styles.rowLast]}>
    <Pressable accessibilityLabel={`Ver detalle de ${item.name}`} accessibilityRole="link" onPress={() => runGuardedNavigation(() => onOpen(item))} style={({ pressed }) => [styles.leading, styles.identity, pressed && styles.pressed]}>
      <EntityIcon entity="supplement" size="compact" />
      <View style={styles.copy}>
        <Text numberOfLines={2} style={styles.name}>{item.name}</Text>
        {item.brand ? <Text numberOfLines={1} style={styles.brand}>{item.brand}</Text> : null}
      </View>
    </Pressable>
    <View style={styles.dose}>
      <Text numberOfLines={2} style={styles.doseValue}>{doseLabel(item.quantity, item.unit)}</Text>
    </View>
  </View>;

  return <><PanelSurface>
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.leading]}>Suplementos</Text>
      <Text style={[styles.headerText, styles.doseHeader]}>Dosis</Text>
    </View>
    {editable ? <ComparisonPanelGestureRows
      actions={(item) => editable ? [
        { backgroundColor: "#515151", icon: <Pencil color={tokens.color.entityIconForeground} size={18} />, label: `Editar dosis de ${item.name}`, onPress: () => openDoseEditor(item) },
        ...(items.length > 1 && onRemove ? [{ backgroundColor: tokens.color.danger, icon: <Trash2 color={tokens.color.entityIconForeground} size={18} />, label: `Quitar ${item.name}`, onPress: () => onRemove(item) }] : []),
      ] : []}
      canDrag={() => editable}
      itemLabel={(item) => item.name}
      items={items}
      onReorder={async (nextItems) => { onReorder?.(nextItems); }}
      renderRow={renderRow}
    /> : <StaticComparisonPanelRows items={items} renderRow={renderRow} />}
  </PanelSurface>
  <ActionSheetModal onRequestClose={closeDoseEditor} visible={editable && editingItem != null}>
    <ActionSheetHeader icon={Pencil} iconColor={tokens.color.supplement} onClose={closeDoseEditor} title="Editar dosis" />
    <View style={styles.doseForm}>
      <Text style={styles.doseSubject}>{editingItem?.name}</Text>
      <Field keyboardType="decimal-pad" label={`Cantidad (${editingItem ? unitLabel(quantity, editingItem.unit) : ""})`} onChangeText={setQuantity} value={quantity} />
      {doseError ? <InlineNotice tone="error">{doseError}</InlineNotice> : null}
      <Button bleed={false} label="Guardar dosis" onPress={saveDose} variant="primary" />
    </View>
  </ActionSheetModal></>;
}

const styles = StyleSheet.create({
  brand: { color: tokens.color.textMuted, fontSize: tokens.type.label, lineHeight: 16 },
  copy: { flex: 1, gap: 2, minWidth: 0 },
  dose: { alignItems: "flex-end", gap: tokens.spacing.xs, justifyContent: "center", paddingRight: 8, width: 116 },
  doseForm: { gap: tokens.spacing.md, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  doseHeader: { paddingRight: 8, textAlign: "right", width: 116 },
  doseSubject: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  doseValue: { color: tokens.color.textMain, fontSize: tokens.type.caption + 1, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, lineHeight: 19, textAlign: "right" },
  header: { minHeight: 40 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textTransform: "uppercase" },
  identity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  itemRow: { minHeight: 76, paddingVertical: tokens.spacing.sm },
  leading: { flex: 1, minWidth: 0, paddingLeft: 8, paddingRight: tokens.spacing.xs },
  name: { color: tokens.color.textMain, fontSize: tokens.type.caption + 1, fontWeight: tokens.weight.medium, lineHeight: 19 },
  pressed: { opacity: 0.68 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
});
