import { ArrowDown, ArrowUp, Check, Copy, Pencil, RotateCcw, Trash2 } from "lucide-react-native";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MacroCalorieDistribution, PanelAllocationBar } from "@/components/nutrition";
import { EntityPanelTabs, PanelBody, PanelEmptyState, PanelSurface } from "@/components/panels";
import { tokens } from "@/design/tokens";
import { EntityIcon } from "@/components/ui";

export type ProgramWeekSummary = {
  allocation: { carbs: number; fat: number; protein: number };
  averageCalories: number;
  calories: number;
  carbsGrams: number;
  dailyPlans: number;
  fatGrams: number;
  id: string;
  proteinGrams: number;
  week: number;
};

type ProgramWeekPanelTab = "calories" | "macros" | "allocation" | "edit";

const tabs = [
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
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

function Header({ columns }: { columns: string[] }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.leadingCell]}>Semana</Text>
      {columns.map((column) => <Text key={column} style={[styles.headerText, styles.dataCell]}>{column}</Text>)}
    </View>
  );
}

function CaloriesPanel({ weeks }: { weeks: ProgramWeekSummary[] }) {
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay datos calóricos." />;
  return (
    <PanelBody>
      <Header columns={["Cal", "Planes", "Prom.", "Vs. ant."]} />
      {weeks.map((week, index) => {
        const previous = weeks[index - 1];
        const delta = previous ? ((week.averageCalories - previous.averageCalories) / previous.averageCalories) * 100 : null;
        return (
          <View key={week.id} style={[styles.row, index === weeks.length - 1 && styles.rowLast]}>
            <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
            <Text style={[styles.cell, styles.dataCell]}>{integer(week.calories)}</Text>
            <Text style={[styles.cell, styles.dataCell]}>{week.dailyPlans}</Text>
            <Text style={[styles.cell, styles.dataCell]}>{integer(week.averageCalories)}</Text>
            <Text style={[styles.cell, styles.dataCell]}>
              {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`}
            </Text>
          </View>
        );
      })}
    </PanelBody>
  );
}

function MacrosPanel({ weeks }: { weeks: ProgramWeekSummary[] }) {
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay datos de macros." />;
  return (
    <PanelBody>
      <Header columns={["P g", "C g", "F g", "PCF"]} />
      {weeks.map((week, index) => (
        <View key={week.id} style={[styles.row, index === weeks.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.proteinGrams)}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.carbsGrams)}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{integer(week.fatGrams)}</Text>
          <MacroCalorieDistribution
            carbsGrams={week.carbsGrams}
            fatGrams={week.fatGrams}
            proteinGrams={week.proteinGrams}
            style={styles.dataCell}
          />
        </View>
      ))}
    </PanelBody>
  );
}

function AllocationPanel({ weeks }: { weeks: ProgramWeekSummary[] }) {
  if (weeks.length === 0) return <PanelEmptyState label="Todavía no hay distribución nutricional." />;
  return (
    <PanelBody>
      <Header columns={["P%", "C%", "F%"]} />
      {weeks.map((week, index) => (
        <View key={week.id} style={[styles.row, styles.allocationRow, index === weeks.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><WeekIdentity week={week.week} /></View>
          <PanelAllocationBar style={styles.dataCell} tone="protein" value={week.allocation.protein} />
          <PanelAllocationBar style={styles.dataCell} tone="carbs" value={week.allocation.carbs} />
          <PanelAllocationBar style={styles.dataCell} tone="fat" value={week.allocation.fat} />
        </View>
      ))}
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

function EditPanel({ initialWeeks }: { initialWeeks: ProgramWeekSummary[] }) {
  const [savedWeeks, setSavedWeeks] = useState(initialWeeks);
  const [draftWeeks, setDraftWeeks] = useState(initialWeeks);
  const dirty = useMemo(() => savedWeeks.map(({ id }) => id).join() !== draftWeeks.map(({ id }) => id).join(), [draftWeeks, savedWeeks]);

  const move = (index: number, offset: number) => {
    const destination = index + offset;
    if (destination < 0 || destination >= draftWeeks.length) return;
    setDraftWeeks((current) => {
      const next = [...current];
      [next[index], next[destination]] = [next[destination], next[index]];
      return next;
    });
  };

  const duplicate = (index: number) => {
    setDraftWeeks((current) => {
      const source = current[index];
      const copy = { ...source, id: `${source.id}-copy-${current.length}`, week: current.length + 1 };
      return [...current.slice(0, index + 1), copy, ...current.slice(index + 1)];
    });
  };

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
            <IconAction disabled={index === 0} label={`Subir Semana ${week.week}`} onPress={() => move(index, -1)}><ArrowUp color={tokens.color.textMuted} size={16} /></IconAction>
            <IconAction disabled={index === draftWeeks.length - 1} label={`Bajar Semana ${week.week}`} onPress={() => move(index, 1)}><ArrowDown color={tokens.color.textMuted} size={16} /></IconAction>
          </View>
          <View style={styles.editIdentity}><WeekIdentity week={week.week} /></View>
          <View style={styles.editActions}>
            <IconAction label={`Duplicar Semana ${week.week}`} onPress={() => duplicate(index)}><Copy color={tokens.color.textMuted} size={16} /></IconAction>
            <IconAction disabled={draftWeeks.length === 1} label={`Eliminar Semana ${week.week}`} onPress={() => setDraftWeeks((current) => current.filter(({ id }) => id !== week.id))}><Trash2 color={tokens.color.danger} size={16} /></IconAction>
          </View>
        </View>
      ))}
      {dirty ? (
        <View style={styles.commitActions}>
          <Pressable accessibilityRole="button" onPress={() => setDraftWeeks(savedWeeks)} style={({ pressed }) => [styles.commitButton, pressed && styles.pressed]}>
            <RotateCcw color={tokens.color.textMain} size={16} /><Text style={styles.commitLabel}>Descartar</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => setSavedWeeks(draftWeeks)} style={({ pressed }) => [styles.commitButton, styles.commitButtonPrimary, pressed && styles.pressed]}>
            <Check color={tokens.color.surfaceApp} size={16} /><Text style={styles.commitLabelPrimary}>Guardar orden</Text>
          </Pressable>
        </View>
      ) : null}
    </PanelBody>
  );
}

export function ProgramWeekComparisonPanels({ weeks }: { weeks: ProgramWeekSummary[] }) {
  const [activeTab, setActiveTab] = useState<ProgramWeekPanelTab>("calories");
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={tabs} />
      {activeTab === "calories" ? <CaloriesPanel weeks={weeks} /> : null}
      {activeTab === "macros" ? <MacrosPanel weeks={weeks} /> : null}
      {activeTab === "allocation" ? <AllocationPanel weeks={weeks} /> : null}
      {activeTab === "edit" ? <EditPanel initialWeeks={weeks} /> : null}
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
