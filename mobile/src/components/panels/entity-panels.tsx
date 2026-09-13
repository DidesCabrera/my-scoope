import { type ReactNode, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Check, ChevronRight, Clock, Pencil, RefreshCw, RotateCcw, Trash2 } from "lucide-react-native";
import { Alert, Pressable, StyleProp, StyleSheet, Text, TextInput, View, ViewStyle } from "react-native";

import { MacroCalorieDistribution, macroCalorieShares, PanelAllocationBar, ProteinPerKilogramBadge } from "@/components/nutrition";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { contextualMacroAllocations } from "./contextual-allocation";
import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "./panel-surface";

type NutritionPanelValues = {
  calories: number;
  calorieShare: number;
  proteinGrams: number;
  proteinPerKilogram?: number | null;
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
  projectedLabel?: string | null;
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
  projectedLabel?: string | null;
};

export type MealMenuFood = {
  name: string;
  quantity: number;
  quantityUnit: string;
};

export type FoodPanelEditing = {
  onDelete(item: FoodPanelItem): Promise<void>;
  onReorder(items: FoodPanelItem[]): Promise<void>;
  onReplace(item: FoodPanelItem): void;
  onUpdateQuantity(item: FoodPanelItem, quantity: number): Promise<void>;
};

export type MealPanelEditing = {
  onDelete(item: MealPanelItem): Promise<void>;
  onOpen(item: MealPanelItem): void;
  onReorder(items: MealPanelItem[]): Promise<void>;
  onReplace(item: MealPanelItem): void;
};

type FoodPanelTab = "quantity" | "calories" | "macros" | "distribution" | "allocation" | "edit";
type MealPanelTab = "menu" | "calories" | "macros" | "distribution" | "allocation" | "edit";

const foodTabs = [
  { key: "quantity", label: "Alimentos" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "distribution", label: "Dist" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: FoodPanelTab; label: string }[];

const mealTabs = [
  { key: "menu", label: "Menú" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "distribution", label: "Dist" },
  { key: "allocation", label: "Alloc" },
] satisfies { key: MealPanelTab; label: string }[];

const editTab = { icon: (selected: boolean) => <Pencil color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={15} />, iconOnly: true, key: "edit", label: "Editar" } as const;

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "0";
}

export function MealRowIdentity({ name, projectedLabel }: { name: string; projectedLabel?: string | null }) {
  return (
    <View style={styles.mealIdentity}>
      <EntityIcon entity="meal" size="compact" />
      <View style={styles.identityCopy}>
        <Text numberOfLines={2} style={styles.mealIdentityName}>{name}</Text>
        {projectedLabel ? <Text style={styles.projectedBadge}>{projectedLabel}</Text> : null}
      </View>
    </View>
  );
}

function isMealPanelItem(item: FoodPanelItem | MealPanelItem): item is MealPanelItem {
  return "foods" in item;
}

function PanelItemName({ item, style = styles.gridLeadingCell }: { item: FoodPanelItem | MealPanelItem; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={style}>
      {isMealPanelItem(item) ? <MealRowIdentity name={item.name} projectedLabel={item.projectedLabel} /> : <View style={styles.identityCopy}><Text numberOfLines={2} style={styles.itemName}>{item.name}</Text>{item.projectedLabel ? <Text style={styles.projectedBadge}>{item.projectedLabel}</Text> : null}</View>}
    </View>
  );
}

function PanelHeaderCell({ align = "center", children, style }: { align?: "center" | "left"; children: ReactNode; style: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.headerCell, style]}>
      <Text style={[styles.headerText, align === "left" && styles.headerTextLeft]}>{children}</Text>
    </View>
  );
}

type FoodPreparation = {
  isPrepared(item: FoodPanelItem): boolean;
  onToggle(item: FoodPanelItem): void;
};

function QuantityHeader({ leadingLabel, preparation, trailingLabel }: { leadingLabel: string; preparation?: boolean; trailingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell align="left" style={styles.quantityLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell style={styles.quantityValue}>{trailingLabel}</PanelHeaderCell>
      {preparation ? <PanelHeaderCell style={styles.preparationValue}>Listo</PanelHeaderCell> : null}
    </View>
  );
}

function MacrosHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell align="left" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell style={styles.ppkValue}>PpK</PanelHeaderCell>
      {(["P", "C", "F"] as const).map((label) => <PanelHeaderCell key={label} style={styles.macroValue}>{label}</PanelHeaderCell>)}
    </View>
  );
}

function DistributionHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell align="left" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      {(["P%", "C%", "F%"] as const).map((label) => <PanelHeaderCell key={label} style={styles.distributionValue}>{label}</PanelHeaderCell>)}
      <PanelHeaderCell style={styles.distributionBar}>P|C|F</PanelHeaderCell>
    </View>
  );
}

function CaloriesHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell align="left" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell style={styles.calorieValue}>Cal</PanelHeaderCell>
      <PanelHeaderCell style={styles.calorieShare}>% Cal</PanelHeaderCell>
    </View>
  );
}

function AllocationHeader({ leadingLabel }: { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header, styles.allocationRow]}>
      <PanelHeaderCell align="left" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      {(["P%", "C%", "F%"] as const).map((label) => <PanelHeaderCell key={label} style={styles.allocationCell}>{label}</PanelHeaderCell>)}
    </View>
  );
}

export function FoodQuantityPanel({ items, preparation }: { items: FoodPanelItem[]; preparation?: FoodPreparation }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay alimentos." />;
  return (
    <PanelBody>
      <QuantityHeader leadingLabel="Alimentos" preparation={Boolean(preparation)} trailingLabel="Qty" />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} style={styles.quantityLeadingCell} />
          <Text style={[styles.cell, styles.quantityValue]}>{decimal(item.quantity)} {item.quantityUnit}</Text>
          {preparation ? (
            <Pressable
              accessibilityLabel={`${preparation.isPrepared(item) ? "Desmarcar" : "Marcar"} ${item.name} como preparado`}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: preparation.isPrepared(item) }}
              hitSlop={8}
              onPress={() => preparation.onToggle(item)}
              style={({ pressed }) => [styles.preparationValue, styles.preparationButton, pressed && styles.pressed]}>
              <View style={styles.preparationMarker}>{preparation.isPrepared(item) ? <View style={styles.preparationMarkerChecked} /> : null}</View>
            </Pressable>
          ) : null}
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
          <View style={[styles.ppkValue, styles.ppkCell]}>
            {item.proteinPerKilogram == null ? <Text style={styles.unavailableValue}>—</Text> : <ProteinPerKilogramBadge showUnit={false} style={styles.ppkBadge} value={item.proteinPerKilogram} />}
          </View>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.fatGrams)}</Text>
        </View>
      ))}
    </PanelBody>
  );
}

export function NutritionDistributionPanel({ items, leadingLabel }: { items: (FoodPanelItem | MealPanelItem)[]; leadingLabel: string }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <DistributionHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => {
        const distribution = macroCalorieShares(item);
        return (
          <View key={item.id} style={[styles.row, index === items.length - 1 && styles.rowLast]}>
            <PanelItemName item={item} />
            <Text style={[styles.cell, styles.distributionValue, styles.proteinDistribution]}>{distribution.protein}%</Text>
            <Text style={[styles.cell, styles.distributionValue, styles.carbsDistribution]}>{distribution.carbs}%</Text>
            <Text style={[styles.cell, styles.distributionValue, styles.fatDistribution]}>{distribution.fat}%</Text>
            <MacroCalorieDistribution {...item} style={styles.distributionBar} />
          </View>
        );
      })}
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
  const allocations = contextualMacroAllocations(items);
  return (
    <PanelBody>
      <AllocationHeader leadingLabel={leadingLabel} />
      {items.map((item, index) => (
        <View key={item.id} style={[styles.row, styles.allocationRow, index === items.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <PanelAllocationBar style={styles.allocationCell} tone="protein" value={allocations[index].protein} />
          <PanelAllocationBar style={styles.allocationCell} tone="carbs" value={allocations[index].carbs} />
          <PanelAllocationBar style={styles.allocationCell} tone="fat" value={allocations[index].fat} />
        </View>
      ))}
    </PanelBody>
  );
}

export function MealMenuPanel({ items, onOpenItem }: { items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay comidas." />;
  return (
    <PanelBody>
      {items.map((item, index) => {
        const canOpen = Boolean((item.detailId != null || item.canOpen) && onOpenItem);
        return (
        <Pressable
          accessibilityLabel={canOpen ? `Ver detalle de ${item.name}` : undefined}
          accessibilityRole={canOpen ? "link" : undefined}
          disabled={!canOpen}
          key={item.id}
          onPress={() => onOpenItem?.(item)}
          style={({ pressed }) => [styles.menuRow, index === items.length - 1 && styles.rowLast, pressed && canOpen && styles.menuRowPressed]}>
          <View style={styles.menuCopy}>
            <View style={styles.menuTitleRow}>
              <MealRowIdentity name={item.name} projectedLabel={item.projectedLabel} />
              {item.time ? (
                <View style={styles.menuTimeGroup}>
                  <Clock color={tokens.color.textMuted} size={11} strokeWidth={2} />
                  <Text style={styles.menuTime}>{item.time}</Text>
                </View>
              ) : null}
            </View>
            <Text style={styles.menuFoods}>
              {item.foods.map((food) => `${food.name} (${decimal(food.quantity)}${food.quantityUnit})`).join(", ")}
            </Text>
          </View>
          {canOpen ? (
            <View style={styles.menuAction}>
              <ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} />
            </View>
          ) : null}
        </Pressable>
        );
      })}
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
              <IconAction disabled={busy} label={`Reemplazar ${item.name}`} onPress={() => editing.onReplace(item)}><RefreshCw color={tokens.color.textMuted} size={16} /></IconAction>
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

export function FoodPanels({ editing, items, preparation }: { editing?: FoodPanelEditing; items: FoodPanelItem[]; preparation?: FoodPreparation }) {
  const [activeTab, setActiveTab] = useState<FoodPanelTab>("quantity");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={editing ? [...foodTabs, editTab] : foodTabs} />
      {activeTab === "quantity" ? <FoodQuantityPanel items={items} preparation={preparation} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel items={items} leadingLabel="Alimentos" /> : null}
      {activeTab === "distribution" ? <NutritionDistributionPanel items={items} leadingLabel="Alimentos" /> : null}
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
      {activeTab === "distribution" ? <NutritionDistributionPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel items={items} leadingLabel="Comidas" /> : null}
      {activeTab === "edit" && editing ? <MealEditPanel editing={editing} items={items} key={items.map(({ id, time }) => `${id}:${time ?? ""}`).join("|")} /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 44, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerCell: { alignSelf: "stretch", justifyContent: "center", minWidth: 0 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, letterSpacing: 0, textAlign: "center", textTransform: "uppercase" },
  headerTextLeft: { paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0 },
  name: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  gridLeadingCell: { alignSelf: "stretch", flexBasis: "40%", flexGrow: 0, flexShrink: 0, justifyContent: "center", minWidth: 0 },
  itemName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 18, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  quantityLeadingCell: { alignSelf: "stretch", flex: 1, justifyContent: "center", minWidth: 0 },
  quantityValue: { textAlign: "center", width: 56 },
  preparationValue: { width: 48 },
  preparationButton: { alignItems: "center", alignSelf: "stretch", justifyContent: "center" },
  preparationMarker: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 2, height: 20, justifyContent: "center", width: 20 },
  preparationMarkerChecked: { backgroundColor: tokens.color.success, borderRadius: 5, height: 10, width: 10 },
  macroValue: { flex: 1, minWidth: 0, textAlign: "center" },
  ppkValue: { flex: 0.9, minWidth: 0 },
  ppkCell: { alignItems: "stretch", justifyContent: "center", paddingHorizontal: 2 },
  ppkBadge: { height: 22, minHeight: 22 },
  unavailableValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
  distributionValue: { flex: 1, minWidth: 0, textAlign: "center" },
  distributionBar: { flex: 1.4, minWidth: 0 },
  proteinDistribution: { color: tokens.color.protein, fontWeight: tokens.weight.semibold },
  carbsDistribution: { color: tokens.color.carbs, fontWeight: tokens.weight.semibold },
  fatDistribution: { color: tokens.color.fat, fontWeight: tokens.weight.semibold },
  calorieValue: { textAlign: "center", width: 54 },
  calorieShare: { flex: 1, minWidth: 92, textAlign: "center" },
  allocationRow: { gap: tokens.spacing.sm },
  allocationCell: { flex: 1, minWidth: 0, width: "auto" },
  menuRow: { alignItems: "center", alignSelf: "stretch", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, paddingLeft: tokens.spacing.sm, paddingRight: tokens.spacing.xs, paddingVertical: tokens.spacing.md },
  menuCopy: { flex: 1, gap: tokens.spacing.compact, minWidth: 0 },
  menuAction: { alignItems: "center", alignSelf: "stretch", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 24 },
  menuRowPressed: { opacity: 0.55 },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  mealIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  identityCopy: { alignItems: "flex-start", flex: 1, gap: 3, justifyContent: "center", minWidth: 0 },
  mealIdentityName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 18 },
  projectedBadge: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: 9, fontWeight: tokens.weight.semibold, overflow: "hidden", paddingHorizontal: 6, paddingVertical: 2 },
  menuTimeGroup: { alignItems: "center", flexDirection: "row", gap: 4, paddingHorizontal: tokens.spacing.xs },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0 },
  menuFoods: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 20, paddingHorizontal: tokens.spacing.xs },
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
