import { ArrowDown, ArrowUp, Check, Copy, Pencil, RotateCcw, Trash2 } from "lucide-react-native";
import { useMemo, useState } from "react";
import { Alert, Pressable, type StyleProp, StyleSheet, Text, View, type ViewStyle } from "react-native";

import { MacroCalorieDistribution, macroCalorieShares, PanelAllocationBar, ProteinPerKilogramBadge } from "@/components/nutrition";
import { contextualMacroAllocations, EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface, SortablePanelHeaderCell, type PanelSortState, useTemporaryPanelSort } from "@/components/panels";
import { tokens } from "@/design/tokens";
import { EntityIcon } from "@/components/ui";
import { ComparisonPanelGestureRows, StaticComparisonPanelRows, type ComparisonPanelAction } from "./comparison-panel-gesture-rows";

export type ProgramWeekSummary = {
  allocation: { carbs: number; fat: number; protein: number };
  averageCalories: number;
  calories: number;
  carbsGrams: number;
  dailyPlans: number;
  fatGrams: number;
  id: string;
  proteinGrams: number;
  ppk: number | null;
  week: number;
};

type ProgramWeekPanelTab = "calories" | "macros" | "distribution" | "allocation" | "edit";

const tabs = [
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "distribution", label: "Dist" },
  { key: "allocation", label: "Alloc" },
  { icon: (selected: boolean) => <Pencil color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={15} />, iconOnly: true, key: "edit", label: "Editar" },
] satisfies Parameters<typeof EntityPanelTabs<ProgramWeekPanelTab>>[0]["tabs"];

function integer(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toLocaleString("es-CL") : "0";
}

function WeekIdentity({ week }: { week: number }) {
  return (
    <View style={styles.weekIdentity}>
      <EntityIcon entity="program" size="compact" />
      <Text style={styles.weekName}>S{week}</Text>
    </View>
  );
}

function Header<Key extends string>({ columns, leadingKey, onSort, sort }: { columns: { key: Key; label: string; style?: StyleProp<ViewStyle> }[]; leadingKey: Key; onSort(key: Key): void; sort: PanelSortState<Key> }) {
  return (
    <View style={[styles.row, styles.header]}>
      <SortablePanelHeaderCell align="left" direction={sort?.key === leadingKey ? sort.direction : undefined} label="Semana" onPress={() => onSort(leadingKey)} style={styles.leadingCell} />
      {columns.map((column) => <SortablePanelHeaderCell direction={sort?.key === column.key ? sort.direction : undefined} key={`${column.key}-${column.label}`} label={column.label} onPress={() => onSort(column.key)} style={[styles.dataCell, column.style]} />)}
    </View>
  );
}

type WeekRowGestures = {
  actions(week: ProgramWeekSummary): ComparisonPanelAction[];
  onReorder(weeks: ProgramWeekSummary[]): Promise<void>;
};

function WeekRows({ gestures, renderRow, weeks }: { gestures?: WeekRowGestures; renderRow(week: ProgramWeekSummary, index: number): React.ReactNode; weeks: ProgramWeekSummary[] }) {
  if (!gestures) return <StaticComparisonPanelRows items={weeks} renderRow={renderRow} />;
  return <ComparisonPanelGestureRows actions={gestures.actions} itemLabel={(week) => `Semana ${week.week}`} items={weeks} onReorder={gestures.onReorder} renderRow={renderRow} />;
}

function CaloriesPanel({ gestures, weeks }: { gestures?: WeekRowGestures; weeks: ProgramWeekSummary[] }) {
  const deltas = new Map(weeks.map((week, index) => {
    const previous = weeks[index - 1];
    return [week.id, previous ? ((week.averageCalories - previous.averageCalories) / previous.averageCalories) * 100 : null] as const;
  }));
  const sorting = useTemporaryPanelSort(weeks, { average: (week) => week.averageCalories, calories: (week) => week.calories, delta: (week) => deltas.get(week.id), plans: (week) => week.dailyPlans, week: (item) => item.week });
  const visibleWeeks = sorting.items;
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay datos calóricos." />;
  return (
    <PanelBody>
      <Header columns={[{ key: "calories", label: "Cal" }, { key: "plans", label: "Planes" }, { key: "average", label: "Prom." }, { key: "delta", label: "Vs. ant." }]} leadingKey="week" {...sorting} />
      <WeekRows gestures={sorting.sort ? undefined : gestures} weeks={visibleWeeks} renderRow={(week, index) => {
        const delta = deltas.get(week.id) ?? null;
        return (
          <View key={week.id} style={[styles.row, index === visibleWeeks.length - 1 && styles.rowLast]}>
            <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
            <Text style={[styles.cell, styles.dataCell]}>{integer(week.calories)}</Text>
            <Text style={[styles.cell, styles.dataCell]}>{week.dailyPlans}</Text>
            <Text style={[styles.cell, styles.dataCell]}>{integer(week.averageCalories)}</Text>
            <Text style={[styles.cell, styles.dataCell]}>
              {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`}
            </Text>
          </View>
        );
      }} />
    </PanelBody>
  );
}

function MacrosPanel({ gestures, weeks }: { gestures?: WeekRowGestures; weeks: ProgramWeekSummary[] }) {
  const sorting = useTemporaryPanelSort(weeks, { carbs: (week) => week.carbsGrams, fat: (week) => week.fatGrams, ppk: (week) => week.ppk, protein: (week) => week.proteinGrams, week: (item) => item.week });
  const visibleWeeks = sorting.items;
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay datos de macros." />;
  return (
    <PanelBody>
      <Header columns={[{ key: "ppk", label: "PpK" }, { key: "protein", label: "P g" }, { key: "carbs", label: "C g" }, { key: "fat", label: "F g" }]} leadingKey="week" {...sorting} />
      <WeekRows gestures={sorting.sort ? undefined : gestures} weeks={visibleWeeks} renderRow={(week, index) => (
        <View key={week.id} style={[styles.row, index === visibleWeeks.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
          <View style={[styles.dataCell, styles.ppkCell]}>{week.ppk == null ? <Text style={styles.emptyValue}>—</Text> : <ProteinPerKilogramBadge showUnit={false} style={styles.ppkBadge} value={week.ppk} />}</View>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.fatGrams)}</Text>
        </View>
      )} />
    </PanelBody>
  );
}

function DistributionPanel({ gestures, weeks }: { gestures?: WeekRowGestures; weeks: ProgramWeekSummary[] }) {
  const sorting = useTemporaryPanelSort(weeks, { carbs: (week) => macroCalorieShares(week).carbs, fat: (week) => macroCalorieShares(week).fat, protein: (week) => macroCalorieShares(week).protein, week: (item) => item.week });
  const visibleWeeks = sorting.items;
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <Header columns={[{ key: "protein", label: "P%" }, { key: "carbs", label: "C%" }, { key: "fat", label: "F%" }, { key: "protein", label: "P|C|F", style: styles.distributionBar }]} leadingKey="week" {...sorting} />
      <WeekRows gestures={sorting.sort ? undefined : gestures} weeks={visibleWeeks} renderRow={(week, index) => {
        const distribution = macroCalorieShares(week);
        return (
          <View key={week.id} style={[styles.row, index === visibleWeeks.length - 1 && styles.rowLast]}>
            <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
            <Text style={[styles.cell, styles.dataCell, styles.proteinDistribution]}>{distribution.protein}%</Text>
            <Text style={[styles.cell, styles.dataCell, styles.carbsDistribution]}>{distribution.carbs}%</Text>
            <Text style={[styles.cell, styles.dataCell, styles.fatDistribution]}>{distribution.fat}%</Text>
            <MacroCalorieDistribution {...week} style={styles.distributionBar} />
          </View>
        );
      }} />
    </PanelBody>
  );
}

function AllocationPanel({ gestures, weeks }: { gestures?: WeekRowGestures; weeks: ProgramWeekSummary[] }) {
  const sourceAllocations = contextualMacroAllocations(weeks);
  const allocationById = new Map(weeks.map((week, index) => [week.id, sourceAllocations[index]]));
  const sorting = useTemporaryPanelSort(weeks, { carbs: (week) => allocationById.get(week.id)?.carbs, fat: (week) => allocationById.get(week.id)?.fat, protein: (week) => allocationById.get(week.id)?.protein, week: (item) => item.week });
  const visibleWeeks = sorting.items;
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  const allocations = contextualMacroAllocations(visibleWeeks);
  return (
    <PanelBody>
      <Header columns={[{ key: "protein", label: "P%" }, { key: "carbs", label: "C%" }, { key: "fat", label: "F%" }]} leadingKey="week" {...sorting} />
      <WeekRows gestures={sorting.sort ? undefined : gestures} weeks={visibleWeeks} renderRow={(week, index) => (
        <View key={week.id} style={[styles.row, styles.allocationRow, index === visibleWeeks.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
          <PanelAllocationBar style={styles.dataCell} tone="protein" value={allocations[index].protein} />
          <PanelAllocationBar style={styles.dataCell} tone="carbs" value={allocations[index].carbs} />
          <PanelAllocationBar style={styles.dataCell} tone="fat" value={allocations[index].fat} />
        </View>
      )} />
    </PanelBody>
  );
}

function IconAction({ disabled = false, label, onPress, children }: { children: React.ReactNode; disabled?: boolean; label: string; onPress(): void }) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.iconAction, disabled && styles.disabled, pressed && styles.pressed]}>
      {children}
    </Pressable>
  );
}

function EditPanel({ initialWeeks, onDelete, onDuplicate, onReorder }: { initialWeeks: ProgramWeekSummary[]; onDelete(week: number): Promise<void>; onDuplicate(week: number): Promise<void>; onReorder(weeks: number[]): Promise<void> }) {
  const [draftWeeks, setDraftWeeks] = useState(initialWeeks);
  const [busy, setBusy] = useState(false);
  const dirty = useMemo(() => initialWeeks.map(({ id }) => id).join() !== draftWeeks.map(({ id }) => id).join(), [draftWeeks, initialWeeks]);

  const move = (index: number, offset: number) => {
    const destination = index + offset;
    if (destination < 0 || destination >= draftWeeks.length) return;
    setDraftWeeks((current) => {
      const next = [...current];
      [next[index], next[destination]] = [next[destination], next[index]];
      return next;
    });
  };

  async function run(action: () => Promise<void>) { setBusy(true); try { await action(); } catch { /* El padre ya presentó el error. */ } finally { setBusy(false); } }

  if (draftWeeks.length === 0) return <PanelEmptyState label="El programa no tiene semanas." />;
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}>
        <Text style={[styles.headerText, styles.editLeading]}>Orden de semanas</Text>
        <Text style={[styles.headerText, styles.editActions]}>Acciones</Text>
      </View>
      {draftWeeks.map((week, index) => (
        <View key={week.id} style={[styles.row, styles.editRow]}>
          <View style={styles.reorderActions}>
            <IconAction disabled={busy || index === 0} label={`Subir Semana ${week.week}`} onPress={() => move(index, -1)}><ArrowUp color={tokens.color.textMuted} size={16} /></IconAction>
            <IconAction disabled={busy || index === draftWeeks.length - 1} label={`Bajar Semana ${week.week}`} onPress={() => move(index, 1)}><ArrowDown color={tokens.color.textMuted} size={16} /></IconAction>
          </View>
          <View style={styles.editIdentity}><WeekIdentity week={week.week} /></View>
          <View style={styles.editActions}>
            <IconAction disabled={busy} label={`Duplicar Semana ${week.week}`} onPress={() => void run(() => onDuplicate(week.week))}><Copy color={tokens.color.textMuted} size={16} /></IconAction>
            <IconAction disabled={busy || draftWeeks.length === 1} label={`Eliminar Semana ${week.week}`} onPress={() => Alert.alert("Eliminar semana", `¿Eliminar la Semana ${week.week} y su planificación?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void run(() => onDelete(week.week)) }])}><Trash2 color={tokens.color.danger} size={16} /></IconAction>
          </View>
        </View>
      ))}
      {dirty ? (
        <View style={styles.commitActions}>
          <Pressable accessibilityRole="button" disabled={busy} onPress={() => setDraftWeeks(initialWeeks)} style={({ pressed }) => [styles.commitButton, pressed && styles.pressed]}>
            <RotateCcw color={tokens.color.textMain} size={16} /><Text style={styles.commitLabel}>Descartar</Text>
          </Pressable>
          <Pressable accessibilityRole="button" disabled={busy} onPress={() => void run(() => onReorder(draftWeeks.map(({ week }) => week)))} style={({ pressed }) => [styles.commitButton, styles.commitButtonPrimary, pressed && styles.pressed]}>
            <Check color={tokens.color.surfaceApp} size={16} /><Text style={styles.commitLabelPrimary}>Guardar orden</Text>
          </Pressable>
        </View>
      ) : null}
    </PanelBody>
  );
}

export function ProgramWeekComparisonPanels({ onDelete, onDuplicate, onReorder, weeks }: { onDelete?: (week: number) => Promise<void>; onDuplicate?: (week: number) => Promise<void>; onReorder?: (weeks: number[]) => Promise<void>; weeks: ProgramWeekSummary[] }) {
  const [activeTab, setActiveTab] = useState<ProgramWeekPanelTab>("calories");
  const sourceSignature = weeks.map(({ id, week }) => `${week}:${id}`).join("|");
  const [optimisticOrder, setOptimisticOrder] = useState<{ sourceSignature: string; weeks: ProgramWeekSummary[] } | null>(null);
  const orderedWeeks = optimisticOrder?.sourceSignature === sourceSignature ? optimisticOrder.weeks : weeks;
  const gestures: WeekRowGestures | undefined = onDelete && onDuplicate && onReorder ? {
    actions: (week) => [
      {
        backgroundColor: "#515151",
        icon: <Copy color={tokens.color.entityIconForeground} size={18} />,
        label: `Duplicar Semana ${week.week}`,
        onPress: () => void onDuplicate(week.week).catch(() => undefined),
      },
      ...(orderedWeeks.length > 1 ? [{
        backgroundColor: "#DB294A",
        icon: <Trash2 color={tokens.color.entityIconForeground} size={18} />,
        label: `Eliminar Semana ${week.week}`,
        onPress: () => Alert.alert("Eliminar semana", `¿Eliminar la Semana ${week.week} y su planificación?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void onDelete(week.week).catch(() => undefined) }]),
      }] : []),
    ],
    onReorder: async (nextWeeks) => {
      const sourceWeekNumbers = nextWeeks.map((week) => weeks.find(({ id }) => id === week.id)?.week ?? week.week);
      const relocatedWeeks = nextWeeks.map((week, index) => ({ ...week, week: orderedWeeks[index].week }));
      setOptimisticOrder({ sourceSignature, weeks: relocatedWeeks });
      try {
        await onReorder(sourceWeekNumbers);
      } catch (error) {
        setOptimisticOrder(null);
        throw error;
      }
    },
  } : undefined;
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={onDelete && onDuplicate && onReorder ? tabs : tabs.filter(({ key }) => key !== "edit")} />
      {activeTab === "calories" ? <CaloriesPanel gestures={gestures} weeks={orderedWeeks} /> : null}
      {activeTab === "macros" ? <MacrosPanel gestures={gestures} weeks={orderedWeeks} /> : null}
      {activeTab === "distribution" ? <DistributionPanel gestures={gestures} weeks={orderedWeeks} /> : null}
      {activeTab === "allocation" ? <AllocationPanel gestures={gestures} weeks={orderedWeeks} /> : null}
      {activeTab === "edit" && onDelete && onDuplicate && onReorder ? <EditPanel initialWeeks={orderedWeeks} key={orderedWeeks.map(({ id }) => id).join("|")} onDelete={onDelete} onDuplicate={onDuplicate} onReorder={onReorder} /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 48, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, textAlign: "center" },
  leadingCell: { flexBasis: "25%", flexGrow: 0, flexShrink: 0, minWidth: 0, textAlign: "left" },
  dataCell: { flex: 1, minWidth: 0 },
  weekIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  weekName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  allocationRow: { gap: tokens.spacing.sm },
  ppkCell: { alignItems: "stretch", justifyContent: "center", paddingHorizontal: 2 },
  ppkBadge: { height: 22, minHeight: 22 },
  emptyValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
  proteinDistribution: { color: tokens.color.protein, fontWeight: tokens.weight.semibold },
  carbsDistribution: { color: tokens.color.carbs, fontWeight: tokens.weight.semibold },
  fatDistribution: { color: tokens.color.fat, fontWeight: tokens.weight.semibold },
  distributionBar: { flex: 1.35, minWidth: 0 },
  editRow: { gap: tokens.spacing.sm },
  reorderActions: { flexDirection: "row", gap: 2 },
  editLeading: { flex: 1, textAlign: "left" },
  editIdentity: { flex: 1, minWidth: 0 },
  editActions: { flexDirection: "row", gap: 2, justifyContent: "flex-end", minWidth: 68 },
  iconAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 34, justifyContent: "center", width: 34 },
  disabled: { opacity: 0.28 },
  pressed: { opacity: 0.68 },
  commitActions: { flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "flex-end", padding: tokens.spacing.sm },
  commitButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.xs, minHeight: 36, paddingHorizontal: tokens.spacing.md },
  commitButtonPrimary: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  commitLabel: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  commitLabelPrimary: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
