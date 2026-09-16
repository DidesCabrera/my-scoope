import { createContext, Fragment, type ReactNode, useContext, useRef, useState } from "react";
import * as Haptics from "expo-haptics";
import { type Href, useRouter } from "expo-router";
import { Check, ChevronRight, Clock, GripVertical, Pencil, RefreshCw, Trash2 } from "lucide-react-native";
import { Alert, Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import DraggableFlatList, { NestableDraggableFlatList, ScaleDecorator, type RenderItemParams } from "react-native-draggable-flatlist";
import ReanimatedSwipeable, { type SwipeableMethods } from "react-native-gesture-handler/ReanimatedSwipeable";

import { MacroCalorieDistribution, macroCalorieShares, PanelAllocationBar, ProteinPerKilogramBadge } from "@/components/nutrition";
import { EntityIcon } from "@/components/ui";
import { useScreenScrollControl } from "@/components/ui/layout";
import { tokens } from "@/design/tokens";
import { contextualMacroAllocations } from "./contextual-allocation";
import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface, SortablePanelHeaderCell } from "./panel-surface";
import { type PanelSortState, useTemporaryPanelSort } from "./temporary-panel-sort";

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
  detailId?: number | null;
  id: string;
  name: string;
  quantity: number;
  quantityUnit: string;
  relationId?: number | null;
  projectedLabel?: string | null;
};

export type MealPanelItem = NutritionPanelValues & {
  canOpen?: boolean;
  completed?: boolean;
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
  onEditPortion(item: FoodPanelItem): void;
  onReorder(items: FoodPanelItem[]): Promise<void>;
  onReplace(item: FoodPanelItem): void;
};

export type MealPanelEditing = {
  onChangeTime(item: MealPanelItem): void;
  onDelete(item: MealPanelItem): Promise<void>;
  onOpen(item: MealPanelItem): void;
  onReorder(items: MealPanelItem[]): Promise<void>;
  onReplace(item: MealPanelItem): void;
};

type FoodPanelTab = "quantity" | "calories" | "macros" | "distribution" | "allocation" | "edit";
type MealPanelTab = "menu" | "calories" | "macros" | "distribution" | "allocation" | "edit";

type EditablePanelItem = { id: string; name: string };
const NestedPanelScrollContext = createContext(true);

type PanelRowEditing<T extends EditablePanelItem> = {
  deleteConfirmation(item: T): { message: string; title: string };
  editLabel(item: T): string;
  onDelete(item: T): Promise<void>;
  onEdit(item: T): void;
  onChangeTime?(item: T): void;
  onReorder(items: T[]): Promise<void>;
  onReplace(item: T): void;
};

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

function SwipeAction({ children, label, onPress, tone = "default" }: { children: ReactNode; label: string; onPress(): void; tone?: "default" | "destructive" | "edit" | "time" }) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.swipeAction,
        tone === "edit" && styles.swipeActionEdit,
        tone === "time" && styles.swipeActionTime,
        tone === "destructive" && styles.swipeActionDestructive,
        pressed && styles.swipeActionPressed,
      ]}>
      {children}
    </Pressable>
  );
}

function confirmRowDeletion<T extends EditablePanelItem>(editing: PanelRowEditing<T>, item: T, afterConfirm?: () => void) {
  const confirmation = editing.deleteConfirmation(item);
  Alert.alert(confirmation.title, confirmation.message, [
    { text: "Cancelar", style: "cancel" },
    {
      text: "Eliminar",
      style: "destructive",
      onPress: () => {
        afterConfirm?.();
        void editing.onDelete(item).catch(() => undefined);
      },
    },
  ]);
}

function beginDrag(drag: () => void, onPrepareDrag?: () => void) {
  onPrepareDrag?.();
  void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid).catch(() => undefined);
  drag();
}

function EditablePanelRow<T extends EditablePanelItem>({ drag, editing, isActive, item, onPrepareDrag, onSwipeableClose, onSwipeableWillOpen, row }: {
  drag(): void;
  editing: PanelRowEditing<T>;
  isActive: boolean;
  item: T;
  onPrepareDrag(): void;
  onSwipeableClose(methods: SwipeableMethods): void;
  onSwipeableWillOpen(methods: SwipeableMethods): void;
  row: ReactNode;
}) {
  const swipeableRef = useRef<SwipeableMethods>(null);
  const accessibilityActions = [
    { name: "activate" as const, label: editing.editLabel(item) },
    ...(editing.onChangeTime ? [{ name: "change-time" as const, label: `Cambiar hora de ${item.name}` }] : []),
    { name: "replace" as const, label: `Reemplazar ${item.name}` },
    { name: "delete" as const, label: `Eliminar ${item.name}` },
  ];

  const renderRightActions = (_progress: unknown, _translation: unknown, methods: SwipeableMethods) => (
    <View style={styles.swipeActions}>
      <SwipeAction label="Editar" onPress={() => { methods.close(); editing.onEdit(item); }} tone="edit"><Pencil color={tokens.color.entityIconForeground} size={18} /></SwipeAction>
      <SwipeAction label="Reemplazar" onPress={() => { methods.close(); editing.onReplace(item); }}><RefreshCw color={tokens.color.entityIconForeground} size={18} /></SwipeAction>
      <SwipeAction label="Eliminar" onPress={() => confirmRowDeletion(editing, item, () => methods.close())} tone="destructive"><Trash2 color={tokens.color.entityIconForeground} size={18} /></SwipeAction>
    </View>
  );
  const renderLeftActions = editing.onChangeTime ? (_progress: unknown, _translation: unknown, methods: SwipeableMethods) => (
    <View style={styles.swipeTimeAction}>
      <SwipeAction label="Cambiar hora" onPress={() => { methods.close(); editing.onChangeTime?.(item); }} tone="time"><Clock color={tokens.color.entityIconForeground} size={19} /></SwipeAction>
    </View>
  ) : undefined;

  return (
    <ScaleDecorator activeScale={1.018}>
      <ReanimatedSwipeable
        friction={2}
        leftThreshold={36}
        onSwipeableClose={() => { if (swipeableRef.current) onSwipeableClose(swipeableRef.current); }}
        onSwipeableWillOpen={() => { if (swipeableRef.current) onSwipeableWillOpen(swipeableRef.current); }}
        overshootFriction={8}
        overshootLeft={false}
        overshootRight={false}
        ref={swipeableRef}
        renderLeftActions={renderLeftActions}
        renderRightActions={renderRightActions}
        rightThreshold={36}>
        <Pressable
            accessibilityActions={accessibilityActions}
            accessibilityHint="Desliza hacia la izquierda para ver acciones. Mantén pulsado y arrastra para reordenar."
            accessibilityLabel={item.name}
            delayLongPress={320}
            disabled={isActive}
            onAccessibilityAction={(event) => {
              if (event.nativeEvent.actionName === "activate") editing.onEdit(item);
              if (event.nativeEvent.actionName === "change-time") editing.onChangeTime?.(item);
              if (event.nativeEvent.actionName === "replace") editing.onReplace(item);
              if (event.nativeEvent.actionName === "delete") confirmRowDeletion(editing, item);
            }}
            onLongPress={() => beginDrag(drag, onPrepareDrag)}
            style={[styles.gestureRow, isActive && styles.gestureRowActive]}>
            {row}
        </Pressable>
      </ReanimatedSwipeable>
    </ScaleDecorator>
  );
}

function PanelRows<T extends EditablePanelItem>({ editing, items, renderRow }: {
  editing?: PanelRowEditing<T>;
  items: T[];
  renderRow(item: T, index: number): ReactNode;
}) {
  const nestedScroll = useContext(NestedPanelScrollContext);
  const { setPanelDragging } = useScreenScrollControl();
  const openSwipeableRef = useRef<SwipeableMethods | null>(null);
  if (!editing) return <>{items.map((item, index) => <Fragment key={item.id}>{renderRow(item, index)}</Fragment>)}</>;

  const handleSwipeableWillOpen = (methods: SwipeableMethods) => {
    if (openSwipeableRef.current && openSwipeableRef.current !== methods) openSwipeableRef.current.close();
    openSwipeableRef.current = methods;
  };
  const handleSwipeableClose = (methods: SwipeableMethods) => {
    if (openSwipeableRef.current === methods) openSwipeableRef.current = null;
  };

  const renderDraggableRow = ({ drag, getIndex, isActive, item }: RenderItemParams<T>) => (
    <EditablePanelRow
      drag={drag}
      editing={editing}
      isActive={isActive}
      item={item}
      onPrepareDrag={() => {
        openSwipeableRef.current?.close();
        openSwipeableRef.current = null;
        if (!nestedScroll) setPanelDragging(true);
      }}
      onSwipeableClose={handleSwipeableClose}
      onSwipeableWillOpen={handleSwipeableWillOpen}
      row={renderRow(item, getIndex() ?? 0)}
    />
  );

  const listProps = {
      activationDistance: 20,
      data: items,
      keyExtractor: (item: T) => item.id,
      onDragBegin: () => {
        openSwipeableRef.current?.close();
        openSwipeableRef.current = null;
        if (!nestedScroll) setPanelDragging(true);
      },
      onDragEnd: ({ data, from, to }: { data: T[]; from: number; to: number }) => {
        if (!nestedScroll) setPanelDragging(false);
        if (from !== to) void editing.onReorder(data).catch(() => undefined);
      },
      onRelease: () => { if (!nestedScroll) setPanelDragging(false); },
      removeClippedSubviews: false,
      renderItem: renderDraggableRow,
      scrollEnabled: false,
    };
  return nestedScroll ? <NestableDraggableFlatList {...listProps} /> : <DraggableFlatList {...listProps} />;
}

export function MealRowIdentity({ completed = false, menu = false, name, projectedLabel }: { completed?: boolean; menu?: boolean; name: string; projectedLabel?: string | null }) {
  return (
    <View style={styles.mealIdentity}>
      <EntityIcon entity="meal" size="compact" />
      <View style={styles.identityCopy}>
        <View style={styles.mealIdentityTitleRow}>
          <Text numberOfLines={2} style={[styles.mealIdentityName, menu && styles.menuMealName]}>{name}</Text>
          {completed ? <View accessibilityLabel="Comida cumplida" style={styles.mealCompleted}><Check color={tokens.color.entityIconForeground} size={12} strokeWidth={3} /></View> : null}
        </View>
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
      {isMealPanelItem(item) ? <MealRowIdentity name={item.name} projectedLabel={item.projectedLabel} /> : <View style={styles.identityCopy}><Text numberOfLines={2} style={[styles.itemName, styles.foodItemName]}>{item.name}</Text>{item.projectedLabel ? <Text style={styles.projectedBadge}>{item.projectedLabel}</Text> : null}</View>}
    </View>
  );
}

type HeaderSortProps<Key extends string> = { onSort(key: Key): void; sort: PanelSortState<Key> };

function PanelHeaderCell<Key extends string>({ align = "center", children, sortKey, style, ...sorting }: HeaderSortProps<Key> & { align?: "center" | "left"; children: string; sortKey: Key; style: StyleProp<ViewStyle> }) {
  return <SortablePanelHeaderCell align={align} direction={sorting.sort?.key === sortKey ? sorting.sort.direction : undefined} label={children} onPress={() => sorting.onSort(sortKey)} style={style} textStyle={align === "left" ? styles.headerTextLeft : undefined} />;
}

type FoodPreparation = {
  disabled?: boolean;
  isPrepared(item: FoodPanelItem): boolean;
  onToggle(item: FoodPanelItem): void;
};

type QuantitySortKey = "name" | "prepared" | "quantity";
function QuantityHeader({ leadingLabel, preparation, trailingLabel, ...sorting }: HeaderSortProps<QuantitySortKey> & { leadingLabel: string; preparation?: boolean; trailingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell {...sorting} align="left" sortKey="name" style={styles.quantityLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell {...sorting} sortKey="quantity" style={styles.quantityValue}>{trailingLabel}</PanelHeaderCell>
      {preparation ? <PanelHeaderCell {...sorting} sortKey="prepared" style={styles.preparationValue}>Listo</PanelHeaderCell> : null}
    </View>
  );
}

type MacrosSortKey = "carbs" | "fat" | "name" | "ppk" | "protein";
function MacrosHeader({ leadingLabel, ...sorting }: HeaderSortProps<MacrosSortKey> & { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell {...sorting} align="left" sortKey="name" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell {...sorting} sortKey="ppk" style={styles.ppkValue}>PpK</PanelHeaderCell>
      {(["P", "C", "F"] as const).map((label) => <PanelHeaderCell {...sorting} key={label} sortKey={{ P: "protein", C: "carbs", F: "fat" }[label]} style={styles.macroValue}>{label}</PanelHeaderCell>)}
    </View>
  );
}

type DistributionSortKey = "carbs" | "fat" | "name" | "protein";
function DistributionHeader({ leadingLabel, ...sorting }: HeaderSortProps<DistributionSortKey> & { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell {...sorting} align="left" sortKey="name" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      {(["P%", "C%", "F%"] as const).map((label) => <PanelHeaderCell {...sorting} key={label} sortKey={{ "P%": "protein", "C%": "carbs", "F%": "fat" }[label]} style={styles.distributionValue}>{label}</PanelHeaderCell>)}
      <PanelHeaderCell {...sorting} sortKey="protein" style={styles.distributionBar}>P|C|F</PanelHeaderCell>
    </View>
  );
}

type CaloriesSortKey = "calories" | "name" | "share";
function CaloriesHeader({ leadingLabel, ...sorting }: HeaderSortProps<CaloriesSortKey> & { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header]}>
      <PanelHeaderCell {...sorting} align="left" sortKey="name" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      <PanelHeaderCell {...sorting} sortKey="calories" style={styles.calorieValue}>Cal</PanelHeaderCell>
      <PanelHeaderCell {...sorting} sortKey="share" style={styles.calorieShare}>% Cal</PanelHeaderCell>
    </View>
  );
}

type AllocationSortKey = "carbs" | "fat" | "name" | "protein";
function AllocationHeader({ leadingLabel, ...sorting }: HeaderSortProps<AllocationSortKey> & { leadingLabel: string }) {
  return (
    <View style={[styles.row, styles.header, styles.allocationRow]}>
      <PanelHeaderCell {...sorting} align="left" sortKey="name" style={styles.gridLeadingCell}>{leadingLabel}</PanelHeaderCell>
      {(["P%", "C%", "F%"] as const).map((label) => <PanelHeaderCell {...sorting} key={label} sortKey={{ "P%": "protein", "C%": "carbs", "F%": "fat" }[label]} style={styles.allocationCell}>{label}</PanelHeaderCell>)}
    </View>
  );
}

export function FoodQuantityPanel({ editing, items, onOpenItem, preparation }: { editing?: PanelRowEditing<FoodPanelItem>; items: FoodPanelItem[]; onOpenItem?: (item: FoodPanelItem) => void; preparation?: FoodPreparation }) {
  const sorting = useTemporaryPanelSort(items, {
    name: (item) => item.name,
    prepared: (item) => preparation?.isPrepared(item) ?? false,
    quantity: (item) => item.quantity,
  });
  const visibleItems = sorting.items;
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay alimentos." />;
  return (
    <PanelBody>
      <QuantityHeader leadingLabel="Alimentos" preparation={Boolean(preparation)} trailingLabel="Qty" {...sorting} />
      <PanelRows editing={sorting.sort ? undefined : editing} items={visibleItems} renderRow={(item, index) => {
        const canOpen = item.detailId != null && Boolean(onOpenItem);
        return <View key={item.id} style={[styles.row, index === visibleItems.length - 1 && styles.rowLast]}>
          {canOpen ? <Pressable accessibilityLabel={`Ver detalle de ${item.name}`} accessibilityRole="link" onPress={() => onOpenItem?.(item)} style={styles.quantityLeadingCell}><PanelItemName item={item} style={styles.foodDetailCopy} /></Pressable> : <PanelItemName item={item} style={styles.quantityLeadingCell} />}
          <Text style={[styles.cell, styles.quantityValue]}>{decimal(item.quantity)} {item.quantityUnit}</Text>
          {preparation ? (
            <Pressable
              accessibilityLabel={`${preparation.isPrepared(item) ? "Desmarcar" : "Marcar"} ${item.name} como preparado`}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: preparation.isPrepared(item), disabled: preparation.disabled }}
              disabled={preparation.disabled}
              hitSlop={8}
              onPress={() => preparation.onToggle(item)}
              style={[styles.preparationValue, styles.preparationButton, preparation.disabled && styles.disabled]}>
              <View style={styles.preparationMarker}>{preparation.isPrepared(item) ? <View style={styles.preparationMarkerChecked} /> : null}</View>
            </Pressable>
          ) : null}
        </View>
      }} />
    </PanelBody>
  );
}

export function NutritionMacrosPanel<T extends FoodPanelItem | MealPanelItem>({ editing, items, leadingLabel }: { editing?: PanelRowEditing<T>; items: T[]; leadingLabel: string }) {
  const sorting = useTemporaryPanelSort(items, {
    carbs: (item) => item.carbsGrams,
    fat: (item) => item.fatGrams,
    name: (item) => item.name,
    ppk: (item) => item.proteinPerKilogram,
    protein: (item) => item.proteinGrams,
  });
  const visibleItems = sorting.items;
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos nutricionales." />;
  return (
    <PanelBody>
      <MacrosHeader leadingLabel={leadingLabel} {...sorting} />
      <PanelRows editing={sorting.sort ? undefined : editing} items={visibleItems} renderRow={(item, index) => (
        <View key={item.id} style={[styles.row, index === visibleItems.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <View style={[styles.ppkValue, styles.ppkCell]}>
            {item.proteinPerKilogram == null ? <Text style={styles.unavailableValue}>—</Text> : <ProteinPerKilogramBadge showUnit={false} style={styles.ppkBadge} value={item.proteinPerKilogram} />}
          </View>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.macroValue]}>{decimal(item.fatGrams)}</Text>
        </View>
      )} />
    </PanelBody>
  );
}

export function NutritionDistributionPanel<T extends FoodPanelItem | MealPanelItem>({ editing, items, leadingLabel }: { editing?: PanelRowEditing<T>; items: T[]; leadingLabel: string }) {
  const sorting = useTemporaryPanelSort(items, {
    carbs: (item) => macroCalorieShares(item).carbs,
    fat: (item) => macroCalorieShares(item).fat,
    name: (item) => item.name,
    protein: (item) => macroCalorieShares(item).protein,
  });
  const visibleItems = sorting.items;
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <DistributionHeader leadingLabel={leadingLabel} {...sorting} />
      <PanelRows editing={sorting.sort ? undefined : editing} items={visibleItems} renderRow={(item, index) => {
        const distribution = macroCalorieShares(item);
        return (
          <View key={item.id} style={[styles.row, index === visibleItems.length - 1 && styles.rowLast]}>
            <PanelItemName item={item} />
            <Text style={[styles.cell, styles.distributionValue, styles.proteinDistribution]}>{distribution.protein}%</Text>
            <Text style={[styles.cell, styles.distributionValue, styles.carbsDistribution]}>{distribution.carbs}%</Text>
            <Text style={[styles.cell, styles.distributionValue, styles.fatDistribution]}>{distribution.fat}%</Text>
            <MacroCalorieDistribution {...item} style={styles.distributionBar} />
          </View>
        );
      }} />
    </PanelBody>
  );
}

export function NutritionCaloriesPanel<T extends FoodPanelItem | MealPanelItem>({ editing, items, leadingLabel }: { editing?: PanelRowEditing<T>; items: T[]; leadingLabel: string }) {
  const sorting = useTemporaryPanelSort(items, {
    calories: (item) => item.calories,
    name: (item) => item.name,
    share: (item) => item.calorieShare,
  });
  const visibleItems = sorting.items;
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay datos calóricos." />;
  return (
    <PanelBody>
      <CaloriesHeader leadingLabel={leadingLabel} {...sorting} />
      <PanelRows editing={sorting.sort ? undefined : editing} items={visibleItems} renderRow={(item, index) => (
        <View key={item.id} style={[styles.row, index === visibleItems.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <Text style={[styles.cell, styles.calorieValue]}>{rounded(item.calories)}</Text>
          <View style={styles.calorieShare}>
            <PanelAllocationBar accessibilityLabel={`${item.name}: ${rounded(item.calorieShare)}% de las calorías`} tone="calories" value={item.calorieShare} />
          </View>
        </View>
      )} />
    </PanelBody>
  );
}

export function NutritionAllocationPanel<T extends FoodPanelItem | MealPanelItem>({ editing, items, leadingLabel }: { editing?: PanelRowEditing<T>; items: T[]; leadingLabel: string }) {
  const sourceAllocations = contextualMacroAllocations(items);
  const allocationById = new Map(items.map((item, index) => [item.id, sourceAllocations[index]]));
  const sorting = useTemporaryPanelSort(items, {
    carbs: (item) => allocationById.get(item.id)?.carbs,
    fat: (item) => allocationById.get(item.id)?.fat,
    name: (item) => item.name,
    protein: (item) => allocationById.get(item.id)?.protein,
  });
  const visibleItems = sorting.items;
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  const allocations = contextualMacroAllocations(visibleItems);
  return (
    <PanelBody>
      <AllocationHeader leadingLabel={leadingLabel} {...sorting} />
      <PanelRows editing={sorting.sort ? undefined : editing} items={visibleItems} renderRow={(item, index) => (
        <View key={item.id} style={[styles.row, styles.allocationRow, index === visibleItems.length - 1 && styles.rowLast]}>
          <PanelItemName item={item} />
          <PanelAllocationBar style={styles.allocationCell} tone="protein" value={allocations[index].protein} />
          <PanelAllocationBar style={styles.allocationCell} tone="carbs" value={allocations[index].carbs} />
          <PanelAllocationBar style={styles.allocationCell} tone="fat" value={allocations[index].fat} />
        </View>
      )} />
    </PanelBody>
  );
}

export function MealMenuPanel({ editing, items, onOpenItem }: { editing?: PanelRowEditing<MealPanelItem>; items: MealPanelItem[]; onOpenItem?: (item: MealPanelItem) => void }) {
  if (items.length === 0) return <PanelEmptyState label="Todavía no hay comidas." />;
  return (
    <PanelBody>
      <PanelRows editing={editing} items={items} renderRow={(item, index) => {
        const canOpen = Boolean((item.detailId != null || item.canOpen) && onOpenItem);
        return (
        <Pressable
          accessibilityLabel={canOpen ? `Ver detalle de ${item.name}` : undefined}
          accessibilityRole={canOpen ? "link" : undefined}
          disabled={!canOpen}
          key={item.id}
          onPress={() => onOpenItem?.(item)}
          style={[styles.menuRow, index === items.length - 1 && styles.rowLast]}>
          <View style={styles.menuCopy}>
            <View style={styles.menuTitleRow}>
              <MealRowIdentity completed={item.completed} menu name={item.name} projectedLabel={item.projectedLabel} />
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
              <ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} />
            </View>
          ) : null}
        </Pressable>
        );
      }} />
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

function EditDragHandle({ disabled, drag, label }: { disabled: boolean; drag(): void; label: string }) {
  return (
    <Pressable
      accessibilityHint="Mantén pulsado y arrastra para cambiar la posición"
      accessibilityLabel={label}
      accessibilityRole="button"
      delayLongPress={180}
      disabled={disabled}
      hitSlop={8}
      onLongPress={() => beginDrag(drag)}
      style={({ pressed }) => [styles.editDragHandle, disabled && styles.disabled, pressed && styles.pressed]}>
      <GripVertical color={tokens.color.textMuted} size={18} strokeWidth={2.2} />
    </Pressable>
  );
}

function FoodEditPanel({ editing, items }: { editing: FoodPanelEditing; items: FoodPanelItem[] }) {
  const [draftItems, setDraftItems] = useState(items);
  const [busy, setBusy] = useState(false);

  if (!draftItems.length) return <PanelEmptyState label="Todavía no hay alimentos para editar." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header, styles.editRow]}><View style={styles.editDragHeader} /><Text style={[styles.headerText, styles.editLeading]}>Alimentos</Text><Text style={[styles.headerText, styles.editValue]}>Porción</Text><Text style={[styles.headerText, styles.foodEditActions]}>Acciones</Text></View>
      <NestableDraggableFlatList
        activationDistance={12}
        data={draftItems}
        keyExtractor={(item) => item.id}
        onDragEnd={({ data, from, to }) => {
          setDraftItems(data);
          if (from === to) return;
          setBusy(true);
          void editing.onReorder(data).catch(() => setDraftItems(items)).finally(() => setBusy(false));
        }}
        renderItem={({ drag, getIndex, isActive, item }) => {
          const index = getIndex() ?? 0;
          return <ScaleDecorator activeScale={1.018}>
          <View style={[styles.editItem, isActive && styles.gestureRowActive, index === draftItems.length - 1 && styles.rowLast]}>
          <View style={[styles.row, styles.editRow]}>
            <EditDragHandle disabled={busy} drag={drag} label={`Reordenar ${item.name}`} />
            <View style={styles.editIdentity}><Text numberOfLines={2} style={[styles.cell, styles.name]}>{item.name}</Text></View>
            <Text style={[styles.cell, styles.editValue, styles.editPortionValue]}>{decimal(item.quantity)} {item.quantityUnit}</Text>
            <View style={[styles.editActions, styles.foodEditActions]}>
              <IconAction disabled={busy} label={`Editar porción de ${item.name}`} onPress={() => editing.onEditPortion(item)}><Pencil color={tokens.color.textMain} size={16} /></IconAction>
              <IconAction disabled={busy} label={`Reemplazar ${item.name}`} onPress={() => editing.onReplace(item)}><RefreshCw color={tokens.color.textMain} size={16} /></IconAction>
              <IconAction disabled={busy} label={`Eliminar ${item.name}`} onPress={() => Alert.alert("Eliminar alimento", `¿Eliminar ${item.name} de esta comida?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void editing.onDelete(item).catch(() => undefined) }])}><Trash2 color={tokens.color.danger} size={16} /></IconAction>
            </View>
          </View>
        </View>
        </ScaleDecorator>;
        }}
        scrollEnabled={false}
      />
    </PanelBody>
  );
}

function MealEditPanel({ editing, items }: { editing: MealPanelEditing; items: MealPanelItem[] }) {
  const [draftItems, setDraftItems] = useState(items);
  const [busy, setBusy] = useState(false);
  if (!draftItems.length) return <PanelEmptyState label="Todavía no hay comidas para editar." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header, styles.editRow]}><View style={styles.editDragHeader} /><Text style={[styles.headerText, styles.editLeading]}>Comidas</Text><Text style={[styles.headerText, styles.editValue]}>Hora</Text><Text style={[styles.headerText, styles.mealEditActions]}>Acciones</Text></View>
      <NestableDraggableFlatList
        activationDistance={12}
        data={draftItems}
        keyExtractor={(item) => item.id}
        onDragEnd={({ data, from, to }) => {
          setDraftItems(data);
          if (from === to) return;
          setBusy(true);
          void editing.onReorder(data).catch(() => setDraftItems(items)).finally(() => setBusy(false));
        }}
        renderItem={({ drag, isActive, item }) => <ScaleDecorator activeScale={1.018}><View style={[styles.row, styles.editRow, isActive && styles.gestureRowActive]}><EditDragHandle disabled={busy} drag={drag} label={`Reordenar ${item.name}`} /><View style={styles.editIdentity}><MealRowIdentity name={item.name} /></View><Text style={[styles.cell, styles.editValue, styles.editTimeValue]}>{item.time ?? "—"}</Text><View style={[styles.editActions, styles.mealEditActions]}>{editing.onChangeTime ? <IconAction disabled={busy} label={`Cambiar hora de ${item.name}`} onPress={() => editing.onChangeTime?.(item)}><Clock color={tokens.color.textMain} size={16} /></IconAction> : null}<IconAction disabled={busy} label={`Editar detalle de ${item.name}`} onPress={() => editing.onOpen(item)}><Pencil color={tokens.color.textMain} size={16} /></IconAction><IconAction disabled={busy} label={`Reemplazar ${item.name}`} onPress={() => editing.onReplace(item)}><RefreshCw color={tokens.color.textMain} size={16} /></IconAction><IconAction disabled={busy} label={`Eliminar ${item.name}`} onPress={() => Alert.alert("Eliminar comida", `¿Eliminar ${item.name} de este plan diario?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void editing.onDelete(item).catch(() => undefined) }])}><Trash2 color={tokens.color.danger} size={16} /></IconAction></View></View></ScaleDecorator>}
        scrollEnabled={false}
      />
    </PanelBody>
  );
}

export function FoodPanels({ editing, items, nestedScroll = false, onOpenItem, preparation, showEditTab = true }: { editing?: FoodPanelEditing; items: FoodPanelItem[]; nestedScroll?: boolean; onOpenItem?: (item: FoodPanelItem) => void; preparation?: FoodPreparation; showEditTab?: boolean }) {
  const [activeTab, setActiveTab] = useState<FoodPanelTab>("quantity");
  const itemSignature = items.map(({ id, name, quantity }) => `${id}:${name}:${quantity}`).join("|");
  const [optimisticOrder, setOptimisticOrder] = useState<{ items: FoodPanelItem[]; sourceSignature: string } | null>(null);
  const orderedItems = optimisticOrder?.sourceSignature === itemSignature ? optimisticOrder.items : items;

  const rowEditing: PanelRowEditing<FoodPanelItem> | undefined = editing ? {
    deleteConfirmation: (item) => ({ message: `¿Eliminar ${item.name} de esta comida?`, title: "Eliminar alimento" }),
    editLabel: (item) => `Editar porción de ${item.name}`,
    onDelete: editing.onDelete,
    onEdit: editing.onEditPortion,
    onReorder: async (nextItems) => {
      setOptimisticOrder({ items: nextItems, sourceSignature: itemSignature });
      try {
        await editing.onReorder(nextItems);
      } catch (error) {
        setOptimisticOrder(null);
        throw error;
      }
    },
    onReplace: editing.onReplace,
  } : undefined;

  return (
    <NestedPanelScrollContext.Provider value={nestedScroll}><PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={editing && showEditTab ? [...foodTabs, editTab] : foodTabs} />
      {activeTab === "quantity" ? <FoodQuantityPanel editing={rowEditing} items={orderedItems} onOpenItem={onOpenItem} preparation={preparation} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel editing={rowEditing} items={orderedItems} leadingLabel="Alimentos" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel editing={rowEditing} items={orderedItems} leadingLabel="Alimentos" /> : null}
      {activeTab === "distribution" ? <NutritionDistributionPanel editing={rowEditing} items={orderedItems} leadingLabel="Alimentos" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel editing={rowEditing} items={orderedItems} leadingLabel="Alimentos" /> : null}
      {activeTab === "edit" && editing ? <FoodEditPanel editing={editing} items={orderedItems} key={orderedItems.map(({ id, quantity }) => `${id}:${quantity}`).join("|")} /> : null}
    </PanelSurface></NestedPanelScrollContext.Provider>
  );
}

export function MealPanels({ editing, items, nestedScroll = false, onOpenItem, showEditTab = true }: { editing?: MealPanelEditing; items: MealPanelItem[]; nestedScroll?: boolean; onOpenItem?: (item: MealPanelItem) => void; showEditTab?: boolean }) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<MealPanelTab>("menu");
  const itemSignature = items.map(({ id, name, time }) => `${id}:${name}:${time ?? ""}`).join("|");
  const [optimisticOrder, setOptimisticOrder] = useState<{ items: MealPanelItem[]; sourceSignature: string } | null>(null);
  const orderedItems = optimisticOrder?.sourceSignature === itemSignature ? optimisticOrder.items : items;
  const openItem = onOpenItem ?? (orderedItems.some((item) => item.detailId != null) ? (item: MealPanelItem) => {
    if (item.detailId != null) router.push(`/libraries/meals/${item.detailId}` as Href);
  } : undefined);

  const rowEditing: PanelRowEditing<MealPanelItem> | undefined = editing ? {
    deleteConfirmation: (item) => ({ message: `¿Eliminar ${item.name} de este plan diario?`, title: "Eliminar comida" }),
    editLabel: (item) => `Editar detalle de ${item.name}`,
    onChangeTime: editing.onChangeTime,
    onDelete: editing.onDelete,
    onEdit: editing.onOpen,
    onReorder: async (nextItems) => {
      setOptimisticOrder({ items: nextItems, sourceSignature: itemSignature });
      try {
        await editing.onReorder(nextItems);
      } catch (error) {
        setOptimisticOrder(null);
        throw error;
      }
    },
    onReplace: editing.onReplace,
  } : undefined;

  return (
    <NestedPanelScrollContext.Provider value={nestedScroll}><PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={editing && showEditTab ? [...mealTabs, editTab] : mealTabs} />
      {activeTab === "menu" ? <MealMenuPanel editing={rowEditing} items={orderedItems} onOpenItem={openItem} /> : null}
      {activeTab === "calories" ? <NutritionCaloriesPanel editing={rowEditing} items={orderedItems} leadingLabel="Comidas" /> : null}
      {activeTab === "macros" ? <NutritionMacrosPanel editing={rowEditing} items={orderedItems} leadingLabel="Comidas" /> : null}
      {activeTab === "distribution" ? <NutritionDistributionPanel editing={rowEditing} items={orderedItems} leadingLabel="Comidas" /> : null}
      {activeTab === "allocation" ? <NutritionAllocationPanel editing={rowEditing} items={orderedItems} leadingLabel="Comidas" /> : null}
      {activeTab === "edit" && editing ? <MealEditPanel editing={editing} items={orderedItems} key={orderedItems.map(({ id, time }) => `${id}:${time ?? ""}`).join("|")} /> : null}
    </PanelSurface></NestedPanelScrollContext.Provider>
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
  foodItemName: { fontWeight: tokens.weight.medium },
  quantityLeadingCell: { alignSelf: "stretch", flex: 1, justifyContent: "center", minWidth: 0 },
  foodDetailCopy: { flex: 1, justifyContent: "center", minWidth: 0 },
  quantityValue: { textAlign: "center", width: 56 },
  preparationValue: { width: 48 },
  preparationButton: { alignItems: "center", alignSelf: "stretch", justifyContent: "center" },
  preparationMarker: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 2, height: 20, justifyContent: "center", width: 20 },
  preparationMarkerChecked: { backgroundColor: tokens.color.food, borderRadius: 5, height: 10, width: 10 },
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
  menuRow: { alignItems: "center", alignSelf: "stretch", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, paddingLeft: tokens.spacing.sm, paddingRight: tokens.spacing.xs, paddingVertical: tokens.spacing.lg },
  menuCopy: { flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  menuAction: { alignItems: "center", alignSelf: "stretch", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 24 },
  menuTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  mealIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  identityCopy: { alignItems: "flex-start", flex: 1, gap: 3, justifyContent: "center", minWidth: 0 },
  mealIdentityTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  mealIdentityName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 18 },
  menuMealName: { fontSize: tokens.type.caption + 1, lineHeight: 19 },
  mealCompleted: { alignItems: "center", backgroundColor: `${tokens.color.meal}1A`, borderColor: tokens.color.meal, borderRadius: tokens.radius.pill, borderWidth: 1, height: 18, justifyContent: "center", width: 18 },
  projectedBadge: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: 9, fontWeight: tokens.weight.semibold, overflow: "hidden", paddingHorizontal: 6, paddingVertical: 2 },
  menuTimeGroup: { alignItems: "center", flexDirection: "row", gap: 4, paddingHorizontal: tokens.spacing.xs },
  menuTime: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, letterSpacing: 0 },
  menuFoods: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, letterSpacing: 0, lineHeight: 20, paddingHorizontal: tokens.spacing.xs },
  gestureRow: { backgroundColor: tokens.color.surfaceMuted },
  gestureRowActive: {
    backgroundColor: tokens.color.surfaceApp,
    borderBottomColor: tokens.color.borderDefault,
    borderBottomWidth: 1,
    borderTopColor: tokens.color.borderDefault,
    borderTopWidth: 1,
    elevation: 4,
    shadowColor: "#000000",
    shadowOffset: { height: 2, width: 0 },
    shadowOpacity: 0.14,
    shadowRadius: 5,
    zIndex: 10,
  },
  swipeActions: { alignSelf: "stretch", flexDirection: "row", width: 144 },
  swipeTimeAction: { alignSelf: "stretch", width: 48 },
  swipeAction: { alignItems: "center", alignSelf: "stretch", backgroundColor: "#515151", flex: 1, justifyContent: "center", width: 48 },
  swipeActionEdit: { backgroundColor: "#515151" },
  swipeActionTime: { backgroundColor: "#1B6491" },
  swipeActionDestructive: { backgroundColor: "#DB294A" },
  swipeActionPressed: { opacity: 0.72 },
  iconAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 34, justifyContent: "center", width: 34 },
  disabled: { opacity: 0.28 },
  pressed: { opacity: 0.68 },
  editItem: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1 },
  editRow: { gap: 0, minHeight: 54 },
  editDragHandle: { alignItems: "center", alignSelf: "stretch", justifyContent: "center", width: 20 },
  editDragHeader: { width: 20 },
  editLeading: { flex: 1, textAlign: "left" },
  editIdentity: { flex: 1, minWidth: 0 },
  editValue: { color: tokens.color.textMuted, fontSize: tokens.type.label, paddingHorizontal: 2, textAlign: "center", width: 54 },
  editPortionValue: { color: tokens.color.textMain },
  editTimeValue: { color: tokens.color.textMain },
  editActions: { flexDirection: "row", justifyContent: "flex-end" },
  foodEditActions: { width: 102 },
  mealEditActions: { width: 136 },
});
