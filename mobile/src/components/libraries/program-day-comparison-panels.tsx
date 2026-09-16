import { GripVertical, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { Alert, Pressable, type StyleProp, StyleSheet, Text, View, type ViewStyle } from "react-native";
import { NestableDraggableFlatList, ScaleDecorator } from "react-native-draggable-flatlist";

import { MacroCalorieDistribution, macroCalorieShares, PanelAllocationBar, ProteinPerKilogramBadge } from "@/components/nutrition";
import { contextualMacroAllocations, EntityPanelTabs, PanelBody, PanelSurface, SortablePanelHeaderCell, type PanelSortState, useTemporaryPanelSort } from "@/components/panels";
import { tokens } from "@/design/tokens";
import { EntityIcon } from "@/components/ui";
import { beginComparisonPanelDrag, ComparisonPanelGestureRows, StaticComparisonPanelRows, type ComparisonPanelAction } from "./comparison-panel-gesture-rows";

type ProgramDayPanelTab = "calories" | "macros" | "distribution" | "allocation" | "edit";

export type ProgramDayNutrition = {
  allocation: { carbs: number; fat: number; protein: number };
  calorieShare: number;
  calories: number;
  carbsGrams: number;
  day: string;
  dayNumber: number;
  fatGrams: number;
  id: string;
  planName: string | null;
  ppk: number;
  proteinGrams: number;
  week: number;
  projectedLabel?: string | null;
};

const tabs = [
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "distribution", label: "Dist" },
  { key: "allocation", label: "Alloc" },
  { icon: (selected: boolean) => <Pencil color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={15} />, iconOnly: true, key: "edit", label: "Editar días" },
] satisfies Parameters<typeof EntityPanelTabs<ProgramDayPanelTab>>[0]["tabs"];

const planNames = ["Día de entrenamiento", "Día equilibrado", "Día de fuerza", "Día de recuperación", "Día alto en carbohidratos", "Día flexible", "Día de descanso"];
const dayNames = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function rowsForWeek(week: number): ProgramDayNutrition[] {
  const emptyIndex = week === 1 ? 5 : 2;
  return dayNames.map((day, index) => {
    const empty = index === emptyIndex;
    return {
      allocation: { carbs: 43 + index % 4, fat: 24 + index % 3, protein: 27 + index % 4 },
      calorieShare: empty ? 0 : 13 + index % 3,
      calories: empty ? 0 : 1980 + index * 35,
      carbsGrams: empty ? 0 : 218 + index * 4,
      day,
      dayNumber: index + 1,
      fatGrams: empty ? 0 : 57 + index,
      id: `week-${week}-day-${index + 1}`,
      planName: empty ? null : planNames[index],
      ppk: empty ? 0 : 1.7 + (index % 3) * 0.1,
      proteinGrams: empty ? 0 : 145 + index * 2,
      week,
    };
  });
}

function DayIdentity({ row }: { row: ProgramDayNutrition }) {
  return (
    <View style={styles.dayIdentity}>
      <EntityIcon entity="dailyPlan" size="compact" />
      <View style={styles.dayCopy}>
        <Text numberOfLines={1} style={styles.dayName}>{row.day}</Text>
        <Text numberOfLines={1} style={styles.planName}>{row.planName ?? "Sin plan"}</Text>
        {row.projectedLabel ? <Text style={styles.projectedBadge}>{row.projectedLabel}</Text> : null}
      </View>
    </View>
  );
}

function Header<Key extends string>({ columns, leadingKey, onSort, sort }: { columns: { key: Key; label: string; style?: StyleProp<ViewStyle> }[]; leadingKey: Key; onSort(key: Key): void; sort: PanelSortState<Key> }) {
  return (
    <View style={[styles.row, styles.header]}>
      <SortablePanelHeaderCell align="left" direction={sort?.key === leadingKey ? sort.direction : undefined} label="Día" onPress={() => onSort(leadingKey)} style={styles.leadingCell} />
      {columns.map((column) => (
        <SortablePanelHeaderCell
          direction={sort?.key === column.key ? sort.direction : undefined}
          key={`${column.key}-${column.label}`}
          label={column.label}
          onPress={() => onSort(column.key)}
          style={[styles.dataCell, column.style]}
        />
      ))}
    </View>
  );
}

type DayRowGestures = {
  actions(row: ProgramDayNutrition): ComparisonPanelAction[];
  onReorder(rows: ProgramDayNutrition[]): Promise<void>;
};

function DayRows({ gestures, renderRow, rows }: { gestures?: DayRowGestures; renderRow(row: ProgramDayNutrition, index: number): React.ReactNode; rows: ProgramDayNutrition[] }) {
  if (!gestures) return <StaticComparisonPanelRows items={rows} renderRow={renderRow} />;
  return <ComparisonPanelGestureRows actions={gestures.actions} itemLabel={(row) => `${row.day}: ${row.planName ?? "Sin plan"}`} items={rows} onReorder={gestures.onReorder} renderRow={renderRow} />;
}

function CaloriesPanel({ gestures, rows }: { gestures?: DayRowGestures; rows: ProgramDayNutrition[] }) {
  const sorting = useTemporaryPanelSort(rows, { calories: (row) => row.calories, day: (row) => row.dayNumber, share: (row) => row.calorieShare });
  const visibleRows = sorting.items;
  return (
    <PanelBody>
      <Header columns={[{ key: "calories", label: "Cal" }, { key: "share", label: "% Cal", style: styles.calorieShareDataCell }]} leadingKey="day" {...sorting} />
      <DayRows gestures={sorting.sort ? undefined : gestures} rows={visibleRows} renderRow={(row, index) => (
        <View key={row.id} style={[styles.row, styles.calorieRow, index === visibleRows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.calories).toLocaleString("es-CL") : "—"}</Text>
          <View style={[styles.dataCell, styles.calorieShareDataCell]}>{row.planName ? <PanelAllocationBar tone="calories" value={row.calorieShare} /> : <Text style={styles.emptyValue}>—</Text>}</View>
        </View>
      )} />
    </PanelBody>
  );
}

function MacrosPanel({ gestures, rows }: { gestures?: DayRowGestures; rows: ProgramDayNutrition[] }) {
  const sorting = useTemporaryPanelSort(rows, { carbs: (row) => row.carbsGrams, day: (row) => row.dayNumber, fat: (row) => row.fatGrams, ppk: (row) => row.ppk, protein: (row) => row.proteinGrams });
  const visibleRows = sorting.items;
  return (
    <PanelBody>
      <Header columns={[{ key: "ppk", label: "PpK", style: styles.ppkDataCell }, { key: "protein", label: "P" }, { key: "carbs", label: "C" }, { key: "fat", label: "F" }]} leadingKey="day" {...sorting} />
      <DayRows gestures={sorting.sort ? undefined : gestures} rows={visibleRows} renderRow={(row, index) => (
        <View key={row.id} style={[styles.row, index === visibleRows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          <View style={[styles.dataCell, styles.ppkDataCell, styles.ppkCell]}>{row.planName ? <ProteinPerKilogramBadge showUnit={false} style={styles.ppkBadge} value={row.ppk} /> : <Text style={styles.emptyValue}>—</Text>}</View>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.proteinGrams) : "—"}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.carbsGrams) : "—"}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.fatGrams) : "—"}</Text>
        </View>
      )} />
    </PanelBody>
  );
}

function DistributionPanel({ gestures, rows }: { gestures?: DayRowGestures; rows: ProgramDayNutrition[] }) {
  const sorting = useTemporaryPanelSort(rows, { carbs: (row) => macroCalorieShares(row).carbs, day: (row) => row.dayNumber, fat: (row) => macroCalorieShares(row).fat, protein: (row) => macroCalorieShares(row).protein });
  const visibleRows = sorting.items;
  return (
    <PanelBody>
      <Header columns={[{ key: "protein", label: "P%" }, { key: "carbs", label: "C%" }, { key: "fat", label: "F%" }, { key: "protein", label: "P|C|F", style: styles.distributionBar }]} leadingKey="day" {...sorting} />
      <DayRows gestures={sorting.sort ? undefined : gestures} rows={visibleRows} renderRow={(row, index) => {
        const distribution = macroCalorieShares(row);
        return (
          <View key={row.id} style={[styles.row, index === visibleRows.length - 1 && styles.rowLast]}>
            <View style={styles.leadingCell}><DayIdentity row={row} /></View>
            <Text style={[styles.cell, styles.dataCell, styles.proteinDistribution]}>{row.planName ? `${distribution.protein}%` : "—"}</Text>
            <Text style={[styles.cell, styles.dataCell, styles.carbsDistribution]}>{row.planName ? `${distribution.carbs}%` : "—"}</Text>
            <Text style={[styles.cell, styles.dataCell, styles.fatDistribution]}>{row.planName ? `${distribution.fat}%` : "—"}</Text>
            <View style={styles.distributionBar}>{row.planName ? <MacroCalorieDistribution {...row} /> : <Text style={styles.emptyValue}>—</Text>}</View>
          </View>
        );
      }} />
    </PanelBody>
  );
}

function AllocationPanel({ gestures, rows }: { gestures?: DayRowGestures; rows: ProgramDayNutrition[] }) {
  const sourceAllocations = contextualMacroAllocations(rows);
  const allocationById = new Map(rows.map((row, index) => [row.id, sourceAllocations[index]]));
  const sorting = useTemporaryPanelSort(rows, { carbs: (row) => allocationById.get(row.id)?.carbs, day: (row) => row.dayNumber, fat: (row) => allocationById.get(row.id)?.fat, protein: (row) => allocationById.get(row.id)?.protein });
  const visibleRows = sorting.items;
  const allocations = contextualMacroAllocations(visibleRows);
  return (
    <PanelBody>
      <Header columns={[{ key: "protein", label: "P%" }, { key: "carbs", label: "C%" }, { key: "fat", label: "F%" }]} leadingKey="day" {...sorting} />
      <DayRows gestures={sorting.sort ? undefined : gestures} rows={visibleRows} renderRow={(row, index) => (
        <View key={row.id} style={[styles.row, styles.allocationRow, index === visibleRows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          {row.planName ? (
            <>
              <PanelAllocationBar style={styles.dataCell} tone="protein" value={allocations[index].protein} />
              <PanelAllocationBar style={styles.dataCell} tone="carbs" value={allocations[index].carbs} />
              <PanelAllocationBar style={styles.dataCell} tone="fat" value={allocations[index].fat} />
            </>
          ) : <Text style={[styles.emptyValue, styles.emptyAllocation]}>Sin distribución</Text>}
        </View>
      )} />
    </PanelBody>
  );
}

function EditPanel({ onAssign, onDelete, onReorder, rows }: { onAssign(week: number, day: number): void; onDelete(week: number, day: number): Promise<void>; onReorder(rows: ProgramDayNutrition[]): Promise<void>; rows: ProgramDayNutrition[] }) {
  const [draftRows, setDraftRows] = useState(rows);
  const [busy, setBusy] = useState(false);
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}>
        <View style={styles.editDragHeader} />
        <Text style={[styles.headerText, styles.editDay]}>Día</Text>
        <Text style={[styles.headerText, styles.editPlan]}>Plan</Text>
        <Text style={[styles.headerText, styles.editActions]}>Acciones</Text>
      </View>
      <NestableDraggableFlatList
        activationDistance={12}
        data={draftRows}
        keyExtractor={(row) => row.id}
        onDragEnd={({ data, from, to }) => {
          setDraftRows(data);
          if (from === to) return;
          setBusy(true);
          void onReorder(data).catch(() => setDraftRows(rows)).finally(() => setBusy(false));
        }}
        renderItem={({ drag, getIndex, isActive, item: row }) => {
          const index = getIndex() ?? 0;
          return <ScaleDecorator activeScale={1.018}><View style={[styles.row, styles.editRow, index === draftRows.length - 1 && styles.rowLast, isActive && styles.editRowActive]}>
          <Pressable accessibilityHint="Mantén pulsado y arrastra para cambiar la posición" accessibilityLabel={`Reordenar plan de ${row.day}`} accessibilityRole="button" delayLongPress={180} disabled={busy} hitSlop={8} onLongPress={() => beginComparisonPanelDrag(drag)} style={({ pressed }) => [styles.editDragHandle, busy && styles.disabled, pressed && styles.pressed]}><GripVertical color={tokens.color.textMuted} size={18} strokeWidth={2.2} /></Pressable>
          <Text style={[styles.cell, styles.editDay]}>{row.day}</Text>
          <Text numberOfLines={2} style={[styles.cell, styles.editPlan, !row.planName && styles.planName]}>{row.planName ?? "Sin plan"}</Text>
          <View style={styles.editActions}>
            <Pressable accessibilityLabel={`${row.planName ? "Reemplazar" : "Agregar"} plan de ${row.day}`} accessibilityRole="button" onPress={() => onAssign(row.week, row.dayNumber)} style={({ pressed }) => [styles.iconAction, pressed && styles.pressed]}>
              {row.planName ? <RefreshCw color={tokens.color.textMain} size={16} /> : <Plus color={tokens.color.textMain} size={17} />}
            </Pressable>
            {row.planName ? <Pressable accessibilityLabel={`Eliminar plan de ${row.day}`} accessibilityRole="button" onPress={() => Alert.alert("Eliminar plan diario", `¿Quitar el plan asignado a ${row.day}?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void onDelete(row.week, row.dayNumber).catch(() => undefined) }])} style={({ pressed }) => [styles.iconAction, pressed && styles.pressed]}><Trash2 color={tokens.color.danger} size={16} /></Pressable> : null}
          </View>
        </View></ScaleDecorator>;
        }}
        scrollEnabled={false}
      />
    </PanelBody>
  );
}

export function ProgramDayComparisonPanels({ onAssign, onDelete, onReorder, rows: providedRows, week }: { onAssign?: (week: number, day: number) => void; onDelete?: (week: number, day: number) => Promise<void>; onReorder?: (week: number, orderedDays: number[]) => Promise<void>; rows?: ProgramDayNutrition[]; week: number }) {
  const [activeTab, setActiveTab] = useState<ProgramDayPanelTab>("calories");
  const sourceRows = providedRows ?? rowsForWeek(week);
  const sourceSignature = sourceRows.map(({ dayNumber, id, planName }) => `${dayNumber}:${id}:${planName ?? ""}`).join("|");
  const [optimisticOrder, setOptimisticOrder] = useState<{ rows: ProgramDayNutrition[]; sourceSignature: string } | null>(null);
  const rows = optimisticOrder?.sourceSignature === sourceSignature ? optimisticOrder.rows : sourceRows;
  const gestures: DayRowGestures | undefined = onAssign && onDelete && onReorder ? {
    actions: (row) => [
      {
        backgroundColor: "#515151",
        icon: row.planName ? <RefreshCw color={tokens.color.entityIconForeground} size={18} /> : <Plus color={tokens.color.entityIconForeground} size={19} />,
        label: `${row.planName ? "Reemplazar" : "Agregar"} plan de ${row.day}`,
        onPress: () => onAssign(row.week, row.dayNumber),
      },
      ...(row.planName ? [{
        backgroundColor: "#DB294A",
        icon: <Trash2 color={tokens.color.entityIconForeground} size={18} />,
        label: `Eliminar plan de ${row.day}`,
        onPress: () => Alert.alert("Eliminar plan diario", `¿Quitar el plan asignado a ${row.day}?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void onDelete(row.week, row.dayNumber).catch(() => undefined) }]),
      }] : []),
    ],
    onReorder: async (nextRows) => {
      const orderedDays = nextRows.map((row) => sourceRows.find(({ id }) => id === row.id)?.dayNumber ?? row.dayNumber);
      const relocatedRows = nextRows.map((row, index) => ({
        ...row,
        day: rows[index].day,
        dayNumber: rows[index].dayNumber,
        week: rows[index].week,
      }));
      setOptimisticOrder({ rows: relocatedRows, sourceSignature });
      try {
        await onReorder(week, orderedDays);
      } catch (error) {
        setOptimisticOrder(null);
        throw error;
      }
    },
  } : undefined;
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={onAssign && onDelete && onReorder ? tabs : tabs.filter(({ key }) => key !== "edit")} />
      {activeTab === "calories" ? <CaloriesPanel gestures={gestures} rows={rows} /> : null}
      {activeTab === "macros" ? <MacrosPanel gestures={gestures} rows={rows} /> : null}
      {activeTab === "distribution" ? <DistributionPanel gestures={gestures} rows={rows} /> : null}
      {activeTab === "allocation" ? <AllocationPanel gestures={gestures} rows={rows} /> : null}
      {activeTab === "edit" && onAssign && onDelete && gestures ? <EditPanel key={rows.map(({ id }) => id).join("|")} onAssign={onAssign} onDelete={onDelete} onReorder={gestures.onReorder} rows={rows} /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 48, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, textAlign: "center" },
  leadingCell: { flexBasis: "38%", flexGrow: 0, flexShrink: 0, minWidth: 0, textAlign: "left" },
  dataCell: { flex: 1, minWidth: 0 },
  calorieShareDataCell: { flex: 1.35 },
  ppkDataCell: { flex: 0.65 },
  dayIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  dayCopy: { flex: 1, minWidth: 0 },
  dayName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  planName: { color: tokens.color.textMuted, fontSize: tokens.type.label, lineHeight: 16 },
  projectedBadge: { alignSelf: "flex-start", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: 9, fontWeight: tokens.weight.semibold, overflow: "hidden", paddingHorizontal: 5, paddingVertical: 1 },
  ppkBadge: { height: 24, minHeight: 24 },
  ppkCell: { paddingHorizontal: 3 },
  emptyValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
  calorieRow: { gap: 3 },
  allocationRow: { gap: tokens.spacing.sm },
  emptyAllocation: { flex: 3 },
  proteinDistribution: { color: tokens.color.protein, fontWeight: tokens.weight.semibold },
  carbsDistribution: { color: tokens.color.carbs, fontWeight: tokens.weight.semibold },
  fatDistribution: { color: tokens.color.fat, fontWeight: tokens.weight.semibold },
  distributionBar: { flex: 1.35, minWidth: 0 },
  editRow: { gap: 0 },
  editRowActive: {
    backgroundColor: "#3a3a3a",
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
  editDragHandle: { alignItems: "center", alignSelf: "stretch", justifyContent: "center", width: 20 },
  editDragHeader: { width: 20 },
  editDay: { flexBasis: "24%", flexGrow: 0, flexShrink: 0, textAlign: "left" },
  editPlan: { flex: 1, minWidth: 0, textAlign: "left" },
  editActions: { flexDirection: "row", justifyContent: "flex-end", minWidth: 66 },
  iconAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 34, justifyContent: "center", width: 34 },
  pressed: { opacity: 0.68 },
  disabled: { opacity: 0.28 },
});
