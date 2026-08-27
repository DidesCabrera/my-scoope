import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Check, ChevronRight, Pencil, RefreshCw, RotateCcw, Trash2 } from "lucide-react-native";
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { MacroCalorieDistribution, PanelAllocationBar } from "@/components/nutrition";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "./panel-surface";

type NutritionPanelValues = {
  calories: number;
  calorieShare: number;
  proteinGrams: number;
  carbsGrams: number;
  fatGrams: number;
  proteinAllocation: number;
  carbsAllocation: number;
  fatAllocation: number;
};

export type FoodPanelItem = NutritionPanelValues & {
  id: string;
  name: string;
  quantity: number;
  quantityUnit: string;
  relationId?: number | null;
};

export type MealPanelItem = NutritionPanelValues & {
  canOpen?: boolean;
  detailId?: number;
  foods: MealMenuFood[];
  id: string;
  name: string;
  note?: string;
  relationId?: number | null;
  time?: string;
};

export type MealMenuFood = {
  name: string;
  quantity: number;
  quantityUnit: string;
};

export type FoodPanelEditing = {
  onDelete(item: FoodPanelItem): Promise<void>;
  onReorder(items: FoodPanelItem[]): Promise<void>;
  onUpdateQuantity(item: FoodPanelItem, quantity: number): Promise<void>;
};

export type MealPanelEditing = {
  onDelete(item: MealPanelItem): Promise<void>;
  onOpen(item: MealPanelItem): void;
  onReorder(items: MealPanelItem[]): Promise<void>;
  onReplace(item: MealPanelItem): void;
};

type FoodPanelTab = "quantity" | "calories" | "macros" | "allocation" | "edit";
type MealPanelTab = "menu" | "calories" | "macros" | "allocation" | "edit";

const foodTabs = [
  { key: "quantity", label: "Alimentos" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: FoodPanelTab; label: string }[];

const mealTabs = [
  { key: "menu", label: "Menú" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: MealPanelTab; label: string }[];

const editTab = { icon: (selected: boolean) => <Pencil color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={15} />, iconOnly: true, key: "edit", label: "Editar" } as const;

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "0";
}

export function MealRowIdentity({ name }: { name: string }) {
  return (
    <View style={styles.mealIdentity}>
      <EntityIcon entity="meal" size="compact" />
      <Text numberOfLines={2} style={styles.mealIdentityName}>{name}</Text>
    </View>
  );
}

function isMealPanelItem(item: FoodPanelItem | MealPanelItem): item is MealPanelItem {
  return "foods" in item;
}

function PanelItemName({ item }: { item: FoodPanelItem | MealPanelItem }) {
  return (
    <View style={styles.gridLeadingCell}>
      {isMealPanelItem(item) ? <MealRowIdentity name={item.name} /> : <Text numberOfLines={2} style={styles.itemName}>{item.name}</Text>}
    </View>
  );
}

function QuantityHeader({ leadingLabel, trailingLabel }: { leadingLabel: string; trailingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name]}>{leadingLabel}</Text>
      <Text style={[styles.headerText, styles.quantityValue]}>{trailingLabel}</Text>
    </View>
  );
}

function MacrosHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      {(["P", "C", "F"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.macroValue]}>{label}</Text>)}
      <Text style={[styles.headerText, styles.distributionCell]}>P|C|F%</Text>
    </View>
  );
}

function CaloriesHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      <Text style={[styles.headerText, styles.calorieValue]}>Cal</Text>
      <Text style={[styles.headerText, styles.calorieShare]}>% Cal</Text>
    </View>
  );
}

function AllocationHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header, styles.allocationRow]}>
      <Text style={[styles.headerText, styles.name, styles.gridLeadingCell]}>{leadingLabel}</Text>
      {(["P%", "C%", "F%"] as const).map((label) => <Text key={label} style={[styles.headerText, styles.allocationCell]}>{label}</Text>)}
    </View>
  );
}

export function FoodQuantityPanel({ items }: { items: FoodPanelItem[] }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay alimentos." />;
  return (
    <PanelBody>
      <QuantityHeader leadingLabel="Alimentos" trailingLabel="Qty" />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.quantityValue]}>{decimal(item.quantity)} {item.quantityUnit}</Text>
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionMacrosPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos nutricionales." />;
  return (
    <PanelBody>
      <MacrosHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.fatGrams)}</Text>
          <MacroCalorieDistribution
            carbsGrams={item.carbsGrams}
            fatGrams={item.fatGrams}
            proteinGrams={item.proteinGrams}
            style={styles.distributionCell}
          />
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionCaloriesPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos calóricos." />;
  return (
    <PanelBody>
      <CaloriesHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.calorieValue]}>{rounded(item.calories)}</Text>
          <View style={styles.calorieShare}>
            <PanelAllocationBar accessibilityLabel={`${item.name}: ${rounded(item.calorieShare)}% de las calorías`} tone="calories" value={item.calorieShare} />
          </View>
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionAllocationPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <AllocationHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, styles.allocationRow, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <PanelAllocationBar style={styles.allocationCell} tone="protein" value={item.proteinAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="carbs" value={item.carbsAllocation} />
          <PanelAllocationBar style={styles.allocationCell} tone="fat" value={item.fatAllocation} />
        </View>
      ))}
    </PanelBody>
  );
}

export function MealMenuPanel({ items, onOpenItem }: { items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay comidas." />;
  return (
    <PanelBody>
      {items.map((item, index) => (
        <View key={item.id} style={[styles.menuRow, index === items.length - 1 && styles.rowLast]}>
          <View style={styles.menuCopy}>
            <View style={styles.menuTitleRow}>
              <MealRowIdentity name={item.name} />
              {item.time ? <Text style={styles.menuTime}>{item.time}</Text> : null}
            </View>
            <Text style={styles.menuFoods}>
              {item.foods.map((food) => `${food.name} (${decimal(food.quantity)}${food.quantityUnit})`).join(", ")}
            </Text>
          </View>
          {(item.detailId != null || item.canOpen) && onOpenItem ? (
            <Pressable
              accessibilityLabel={`Ver detalle de ${item.name}`}
              accessibilityRole="link"
              hitSlop={8}
              onPress={() => onOpenItem(item)}
              style={({ pressed }) => [styles.menuAction, pressed && styles.menuActionPressed]}>
              <ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} />
            </Pressable>
          ) : null}
        </View>
      ))}
    </PanelBody>
  );
}

function IconAction({ disabled = false, label, onPress, children }: { children: React.ReactNode; disabled?: boolean; label: string; onPress(): void }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.iconAction, disabled && styles.disabled, pressed && styles.pressed]}>
      {children}
    </Pressable>
  );
}

function moveItem<T>(items: T[], index: number, offset: number): T[] {
  const destination = index + offset;
  if (destination < 0 || destination >= items.length) return items;
  const next = [...items];
  [next[index], next[destination]] = [next[destination], next[index]];
  return next;
}

function FoodEditPanel({ editing, items }: { editing: FoodPanelEditing; items: FoodPanelItem[] }) {
  const [draftItems, setDraftItems] = useState(items);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);
  const dirty = useMemo(() => draftItems.map(({ id }) => id).join() !== items.map(({ id }) => id).join(), [draftItems, items]);

  async function saveOrder() {
    setBusy(true);
    try { await editing.onReorder(draftItems); } catch { /* El padre ya presentó el error. */ } finally { setBusy(false); }
  }

  async function saveQuantity(item: FoodPanelItem) {
    const value = Number(quantity.replace(",", "."));
    if (!Number.isFinite(value) || value <= 0) {
      Alert.alert("Porción inválida", "Ingresa una cantidad mayor que cero.");
      return;
    }
    setBusy(true);
    try { await editing.onUpdateQuantity(item, value); setEditingId(null); } catch { /* Conserva el editor abierto. */ } finally { setBusy(false); }
  }

  if (!draftItems.length) return <PanelEmptyState label="Todavía no hay alimentos para editar." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}><Text style={[styles.headerText, styles.editLeading]}>Alimentos</Text><Text style={[styles.headerText, styles.editActions]}>Acciones</Text></View>
      {draftItems.map((item, index) => (
        <View key={item.id} style={[styles.editItem, index === draftItems.length - 1 && !dirty && styles.rowLast]}>
          <View style={[styles.row, styles.editRow]}>
            <View style={styles.reorderActions}>
              <IconAction disabled={busy || index === 0} label={`Subir ${item.name}`} onPress={() => setDraftItems((current) => moveItem(current, index, -1))}><ArrowUp color={tokens.color.textMuted} size={16} /></IconAction>
              <IconAction disabled={busy || index === draftItems.length - 1} label={`Bajar ${item.name}`} onPress={() => setDraftItems((current) => moveItem(current, index, 1))}><ArrowDown color={tokens.color.textMuted} size={16} /></IconAction>
            </View>
            <View style={styles.editIdentity}><Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text><Text style={styles.editMeta}>{decimal(item.quantity)} {item.quantityUnit}</Text></View>
            <View style={styles.editActions}>
              <IconAction disabled={busy} label={`Editar porción de ${item.name}`} onPress={() => { setEditingId(item.id); setQuantity(String(item.quantity)); }}><Pencil color={tokens.color.textMuted} size={16} /></IconAction>
              <IconAction disabled={busy} label={`Eliminar ${item.name}`} onPress={() => Alert.alert("Eliminar alimento", `¿Eliminar ${item.name} de esta comida?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void editing.onDelete(item).catch(() => undefined) }])}><Trash2 color={tokens.color.danger} size={16} /></IconAction>
            </View>
          </View>
          {editingId === item.id ? <View style={styles.inlineEdit}><TextInput accessibilityLabel={`Porción de ${item.name}`} keyboardType="decimal-pad" onChangeText={setQuantity} style={styles.inlineInput} value={quantity} /><Text style={styles.inlineUnit}>{item.quantityUnit}</Text><IconAction disabled={busy} label="Guardar porción" onPress={() => void saveQuantity(item)}><Check color={tokens.color.textMain} size={17} /></IconAction><IconAction disabled={busy} label="Cancelar edición" onPress={() => setEditingId(null)}><RotateCcw color={tokens.color.textMuted} size={16} /></IconAction></View> : null}
        </View>
      ))}
      {dirty ? <View style={styles.commitActions}><Pressable accessibilityRole="button" disabled={busy} onPress={() => setDraftItems(items)} style={({ pressed }) => [styles.commitButton, pressed && styles.pressed]}><RotateCcw color={tokens.color.textMain} size={16} /><Text style={styles.commitLabel}>Descartar</Text></Pressable><Pressable accessibilityRole="button" disabled={busy} onPress={() => void saveOrder()} style={({ pressed }) => [styles.commitButton, styles.commitButtonPrimary, pressed && styles.pressed]}><Check color={tokens.color.surfaceApp} size={16} /><Text style={styles.commitLabelPrimary}>Guardar orden</Text></Pressable></View> : null}
    </PanelBody>
  );
}

function MealEditPanel({ editing, items }: { editing: MealPanelEditing; items: MealPanelItem[] }) {
  const [draftItems, setDraftItems] = useState(items);
  const [busy, setBusy] = useState(false);
  const dirty = useMemo(() => draftItems.map(({ id }) => id).join() !== items.map(({ id }) => id).join(), [draftItems, items]);
  async function saveOrder() { setBusy(true); try { await editing.onReorder(draftItems); } catch { /* El padre ya presentó el error. */ } finally { setBusy(false); } }
  if (!draftItems.length) return <PanelEmptyState label="Todavía no hay comidas para editar." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}><Text style={[styles.headerText, styles.editLeading]}>Comidas</Text><Text style={[styles.headerText, styles.editActions]}>Acciones</Text></View>
      {draftItems.map((item, index) => <View key={item.id} style={[styles.row, styles.editRow]}><View style={styles.reorderActions}><IconAction disabled={busy || index === 0} label={`Subir ${item.name}`} onPress={() => setDraftItems((current) => moveItem(current, index, -1))}><ArrowUp color={tokens.color.textMuted} size={16} /></IconAction><IconAction disabled={busy || index === draftItems.length - 1} label={`Bajar ${item.name}`} onPress={() => setDraftItems((current) => moveItem(current, index, 1))}><ArrowDown color={tokens.color.textMuted} size={16} /></IconAction></View><View style={styles.editIdentity}><MealRowIdentity name={item.name} />{item.time ? <Text style={styles.editMeta}>{item.time}</Text> : null}</View><View style={styles.editActions}><IconAction disabled={busy} label={`Editar detalle de ${item.name}`} onPress={() => editing.onOpen(item)}><Pencil color={tokens.color.textMuted} size={16} /></IconAction><IconAction disabled={busy} label={`Reemplazar ${item.name}`} onPress={() => editing.onReplace(item)}><RefreshCw color={tokens.color.textMuted} size={16} /></IconAction><IconAction disabled={busy} label={`Eliminar ${item.name}`} onPress={() => Alert.alert("Eliminar comida", `¿Eliminar ${item.name} de este plan diario?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void editing.onDelete(item).catch(() => undefined) }])}><Trash2 color={tokens.color.danger} size={16} /></IconAction></View></View>)}
      {dirty ? <View style={styles.commitActions}><Pressable accessibilityRole="button" disabled={busy} onPress={() => setDraftItems(items)} style={({ pressed }) => [styles.commitButton, pressed && styles.pressed]}><RotateCcw color={tokens.color.textMain} size={16} /><Text style={styles.commitLabel}>Descartar</Text></Pressable><Pressable accessibilityRole="button" disabled={busy} onPress={() => void saveOrder()} style={({ pressed }) => [styles.commitButton, styles.commitButtonPrimary, pressed && styles.pressed]}><Check color={tokens.color.surfaceApp} size={16} /><Text style={styles.commitLabelPrimary}>Guardar orden</Text></Pressable></View> : null}
    </PanelBody>
  );
}

export function FoodPanels({ editing, items }: { editing?: FoodPanelEditing; items: FoodPanelItem[] }) {
  const [activeTab, setActiveTab] = useState<FoodPanelTab>("quantity");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={editing ? [...foodTabs, editTab] : foodTabs} />
      {activeTab === "quantity" ? <FoodQuantityPanel items={items} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "edit" && editing ? <FoodEditPanel editing={editing} items={items} key={items.map(({ id, quantity }) => `${id}:${quantity}`).join("|")} /> : null}
    </PanelSurface>
  );
}

export function MealPanels({ editing, items, onOpenItem }: { editing?: MealPanelEditing; items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  const [activeTab, setActiveTab] = useState<MealPanelTab>("menu");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={editing ? [...mealTabs, editTab] : mealTabs} />
      {activeTab === "menu" ? <MealMenuPanel items={items} onOpenItem={onOpenItem} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "edit" && editing ? <MealEditPanel editing={editing} items={items} key={items.map(({ id, time }) => `${id}:${time ?? ""}`).join("|")} /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, letterSpacing: 0, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0 },
  name: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  gridLeadingCell: { alignSelf: "stretch", flexBasis: "40%", flexGrow: 0, flexShrink: 0, justifyContent: "center", minWidth: 0 },
  itemName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 18, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  quantityValue: { textAlign: "right", width: 88 },
  macroValue: { flex: 1, minWidth: 0, textAlign: "center" },
  distributionCell: { flex: 1.4, minWidth: 0 },
  calorieValue: { textAlign: "center", width: 54 },
  calorieShare: { flex: 1, minWidth: 92, textAlign: "center" },
  allocationRow: { gap: tokens.spacing.sm },
  allocationCell: { flex: 1, minWidth: 0, width: "auto" },
  menuRow: { alignItems: "center", alignSelf: "stretch", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.md },
  menuCopy: { flex: 1, gap: tokens.spacing.compact, minWidth: 0 },
  menuAction: { alignItems: "center", alignSelf: "stretch", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 32 },
  menuActionPressed: { opacity: 0.55 },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  mealIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  mealIdentityName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 18 },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0, paddingHorizontal: tokens.spacing.xs },
  menuFoods: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 20, opacity: 0.82, paddingHorizontal: tokens.spacing.xs },
  iconAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 34, justifyContent: "center", width: 34 },
  disabled: { opacity: 0.28 },
  pressed: { opacity: 0.68 },
  editItem: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1 },
  editRow: { gap: tokens.spacing.xs, minHeight: 54 },
  reorderActions: { flexDirection: "row" },
  editLeading: { flex: 1, textAlign: "left" },
  editIdentity: { flex: 1, minWidth: 0 },
  editMeta: { color: tokens.color.textMuted, fontSize: tokens.type.label, paddingHorizontal: tokens.spacing.xs },
  editActions: { flexDirection: "row", justifyContent: "flex-end" },
  inlineEdit: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.spacing.sm },
  inlineInput: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, flex: 1, minHeight: 40, paddingHorizontal: tokens.spacing.md },
  inlineUnit: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  commitActions: { flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "flex-end", padding: tokens.spacing.sm },
  commitButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minHeight: 36, paddingHorizontal: tokens.spacing.md },
  commitButtonPrimary: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  commitLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  commitLabelPrimary: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
