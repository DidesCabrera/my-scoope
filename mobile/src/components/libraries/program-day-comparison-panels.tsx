import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MacroCalorieDistribution, PanelAllocationBar } from "@/components/nutrition";
import { EntityPanelTabs, PanelBody, PanelSurface } from "@/components/panels";
import { tokens } from "@/design/tokens";
import { EntityIcon } from "@/components/ui";

type ProgramDayPanelTab = "calories" | "macros" | "allocation" | "edit";

export type ProgramDayNutrition = {
  allocation: { carbs: number; fat: number; protein: number };
  calorieShare: number;
  calories: number;
  carbsGrams: number;
  day: string;
  fatGrams: number;
  id: string;
  planName: string | null;
  ppk: number;
  proteinGrams: number;
};

const tabs = [
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
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
      fatGrams: empty ? 0 : 57 + index,
      id: `week-${week}-day-${index + 1}`,
      planName: empty ? null : planNames[index],
      ppk: empty ? 0 : 1.7 + (index % 3) * 0.1,
      proteinGrams: empty ? 0 : 145 + index * 2,
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
      </View>
    </View>
  );
}

function Header({ columns }: { columns: string[] }) {
  return (
    <View style={[styles.row, styles.header]}>
      <Text style={[styles.headerText, styles.leadingCell]}>Día</Text>
      {columns.map((column) => <Text key={column} style={[styles.headerText, styles.dataCell]}>{column}</Text>)}
    </View>
  );
}

function CaloriesPanel({ rows }: { rows: ProgramDayNutrition[] }) {
  return (
    <PanelBody>
      <Header columns={["Cal", "% Cal", "PPK"]} />
      {rows.map((row, index) => (
        <View key={row.id} style={[styles.row, styles.calorieRow, index === rows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.calories).toLocaleString("es-CL") : "—"}</Text>
          <View style={styles.dataCell}>{row.planName ? <PanelAllocationBar size="compact" tone="calories" value={row.calorieShare} /> : <Text style={styles.emptyValue}>—</Text>}</View>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? row.ppk.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : "—"}</Text>
        </View>
      ))}
    </PanelBody>
  );
}

function MacrosPanel({ rows }: { rows: ProgramDayNutrition[] }) {
  return (
    <PanelBody>
      <Header columns={["P", "C", "F", "PCF"]} />
      {rows.map((row, index) => (
        <View key={row.id} style={[styles.row, index === rows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.proteinGrams) : "—"}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.carbsGrams) : "—"}</Text>
          <Text style={[styles.cell, styles.dataCell]}>{row.planName ? Math.round(row.fatGrams) : "—"}</Text>
          <View style={styles.dataCell}>{row.planName ? <MacroCalorieDistribution carbsGrams={row.carbsGrams} fatGrams={row.fatGrams} proteinGrams={row.proteinGrams} /> : <Text style={styles.emptyValue}>—</Text>}</View>
        </View>
      ))}
    </PanelBody>
  );
}

function AllocationPanel({ rows }: { rows: ProgramDayNutrition[] }) {
  return (
    <PanelBody>
      <Header columns={["P%", "C%", "F%"]} />
      {rows.map((row, index) => (
        <View key={row.id} style={[styles.row, styles.allocationRow, index === rows.length - 1 && styles.rowLast]}>
          <View style={styles.leadingCell}><DayIdentity row={row} /></View>
          {row.planName ? (
            <>
              <PanelAllocationBar size="compact" style={styles.dataCell} tone="protein" value={row.allocation.protein} />
              <PanelAllocationBar size="compact" style={styles.dataCell} tone="carbs" value={row.allocation.carbs} />
              <PanelAllocationBar size="compact" style={styles.dataCell} tone="fat" value={row.allocation.fat} />
            </>
          ) : <Text style={[styles.emptyValue, styles.emptyAllocation]}>Sin distribución</Text>}
        </View>
      ))}
    </PanelBody>
  );
}

function EditPanel({ rows }: { rows: ProgramDayNutrition[] }) {
  return (
    <PanelBody>
      <View style={[styles.row, styles.header]}>
        <Text style={[styles.headerText, styles.editDay]}>Día</Text>
        <Text style={[styles.headerText, styles.editPlan]}>Plan</Text>
        <Text style={[styles.headerText, styles.editActions]}>Acciones</Text>
      </View>
      {rows.map((row, index) => (
        <View key={row.id} style={[styles.row, styles.editRow, index === rows.length - 1 && styles.rowLast]}>
          <Text style={[styles.cell, styles.editDay]}>{row.day}</Text>
          <Text numberOfLines={2} style={[styles.cell, styles.editPlan, !row.planName && styles.planName]}>{row.planName ?? "Sin plan"}</Text>
          <View style={styles.editActions}>
            <Pressable accessibilityLabel={`${row.planName ? "Reemplazar" : "Agregar"} plan de ${row.day}`} accessibilityRole="button" style={({ pressed }) => [styles.iconAction, pressed && styles.pressed]}>
              {row.planName ? <RefreshCw color={tokens.color.textMuted} size={16} /> : <Plus color={tokens.color.dailyPlan} size={17} />}
            </Pressable>
            {row.planName ? <Pressable accessibilityLabel={`Eliminar plan de ${row.day}`} accessibilityRole="button" style={({ pressed }) => [styles.iconAction, pressed && styles.pressed]}><Trash2 color={tokens.color.danger} size={16} /></Pressable> : null}
          </View>
        </View>
      ))}
    </PanelBody>
  );
}

export function ProgramDayComparisonPanels({ rows: providedRows, week }: { rows?: ProgramDayNutrition[]; week: number }) {
  const [activeTab, setActiveTab] = useState<ProgramDayPanelTab>("calories");
  const rows = providedRows ?? rowsForWeek(week);
  return (
    <PanelSurface>
      <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={tabs} />
      {activeTab === "calories" ? <CaloriesPanel rows={rows} /> : null}
      {activeTab === "macros" ? <MacrosPanel rows={rows} /> : null}
      {activeTab === "allocation" ? <AllocationPanel rows={rows} /> : null}
      {activeTab === "edit" ? <EditPanel rows={rows} /> : null}
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 48, paddingHorizontal: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textAlign: "center", textTransform: "uppercase" },
  cell: { color: tokens.color.textMain, fontSize: 11, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, textAlign: "center" },
  leadingCell: { flexBasis: "38%", flexGrow: 0, flexShrink: 0, minWidth: 0, textAlign: "left" },
  dataCell: { flex: 1, minWidth: 0 },
  dayIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  dayCopy: { flex: 1, minWidth: 0 },
  dayName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  planName: { color: tokens.color.textMuted, fontSize: 10, lineHeight: 14 },
  emptyValue: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center" },
  calorieRow: { gap: 3 },
  allocationRow: { gap: 3 },
  emptyAllocation: { flex: 3 },
  editRow: { gap: tokens.spacing.sm },
  editDay: { flexBasis: "24%", flexGrow: 0, flexShrink: 0, textAlign: "left" },
  editPlan: { flex: 1, minWidth: 0, textAlign: "left" },
  editActions: { flexDirection: "row", justifyContent: "flex-end", minWidth: 66 },
  iconAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 30, justifyContent: "center", width: 30 },
  pressed: { opacity: 0.68 },
});
