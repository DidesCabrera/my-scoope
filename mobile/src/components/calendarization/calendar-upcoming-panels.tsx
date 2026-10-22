import { useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { Pencil, RefreshCw, Trash2 } from "lucide-react-native";

import type { CalendarDay } from "@/api/types";
import { MacroCalorieDistribution, macroCalorieShares, PanelAllocationBar, ProteinPerKilogramBadge } from "@/components/nutrition";
import { EntityPanelTabs, PanelBody, PanelSurface } from "@/components/panels";
import { ComparisonPanelGestureRows } from "@/components/libraries/comparison-panel-gesture-rows";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { runGuardedNavigation } from "@/navigation/navigation-press-guard";

type Tab = "plans" | "calories" | "macros" | "distribution";

const tabs = [
  { key: "plans", label: "Planes" },
  { key: "calories", label: "Calorías" },
  { key: "macros", label: "Macros" },
  { key: "distribution", label: "Dist" },
] satisfies Parameters<typeof EntityPanelTabs<Tab>>[0]["tabs"];

function dateLabel(value: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("es-CL", options).format(new Date(`${value}T12:00:00`));
}

function number(value: number | null | undefined): number | null {
  return value != null && Number.isFinite(value) ? value : null;
}

function integer(value: number | null | undefined): string {
  const valid = number(value);
  return valid == null ? "—" : Math.round(valid).toLocaleString("es-CL");
}

function PlanIdentity({ day, tab }: { day: CalendarDay; tab: Tab }) {
  return (
    <View style={styles.identity}>
      {tab === "plans" ? <View style={styles.dateColumn}>
        <Text style={styles.dateWeekday}>{dateLabel(day.calendar_date, { weekday: "short" })}</Text>
        <Text style={styles.dateNumber}>{day.calendar_date.slice(8, 10)}</Text>
      </View> : null}
      <View style={styles.planCopy}>
        <View style={styles.planTitleRow}>
          {day.has_plan ? <EntityIcon entity="dailyPlan" size="compact" /> : null}
          <Text numberOfLines={2} style={styles.planName}>{day.has_plan ? day.plan_name : "Sin plan asignado"}</Text>
        </View>
        {tab === "plans"
          ? day.has_plan && day.source_program_name ? <Text numberOfLines={1} style={styles.subtitle}>{day.source_program_name}</Text> : null
          : <Text style={styles.subtitle}>{dateLabel(day.calendar_date, { weekday: "short", day: "numeric", month: "short" })}</Text>}
      </View>
    </View>
  );
}

function Header({ tab }: { tab: Exclude<Tab, "plans"> }) {
  return <View style={[styles.analyticsRow, styles.header]}>
    <Text style={[styles.headerLabel, styles.leading]}>Plan diario</Text>
    {tab === "calories" ? <>
      <Text style={[styles.headerLabel, styles.calorieCell]}>Cal</Text>
      <Text style={[styles.headerLabel, styles.shareCell]}>% Cal</Text>
    </> : null}
    {tab === "macros" ? <>
      <Text style={[styles.headerLabel, styles.ppkCell]}>PpK</Text>
      <Text style={[styles.headerLabel, styles.macroCell]}>P</Text>
      <Text style={[styles.headerLabel, styles.macroCell]}>C</Text>
      <Text style={[styles.headerLabel, styles.macroCell]}>F</Text>
    </> : null}
    {tab === "distribution" ? <>
      <Text style={[styles.headerLabel, styles.percentCell]}>P%</Text>
      <Text style={[styles.headerLabel, styles.percentCell]}>C%</Text>
      <Text style={[styles.headerLabel, styles.percentCell]}>F%</Text>
      <Text style={[styles.headerLabel, styles.distributionCell]}>P|C|F</Text>
    </> : null}
  </View>;
}

type RowItem = { id: string; day: CalendarDay };

export function CalendarUpcomingPanels({ days, onOpenDay, onRemove, onReorder, onReplace }: {
  days: CalendarDay[];
  onOpenDay(day: CalendarDay): void;
  onRemove(day: CalendarDay): Promise<void>;
  onReorder(dates: string[], orderedDayIds: (number | null)[]): Promise<void>;
  onReplace(day: CalendarDay): void;
}) {
  const [activeTab, setActiveTab] = useState<Tab>("plans");
  const [optimistic, setOptimistic] = useState<{ signature: string; items: RowItem[] } | null>(null);
  const signature = days.map((day) => `${day.calendar_date}:${day.id ?? "empty"}`).join("|");
  const sourceItems = days.map((day) => ({ id: day.id == null ? `empty-${day.calendar_date}` : `plan-${day.id}`, day }));
  const items = optimistic?.signature === signature ? optimistic.items : sourceItems;
  const visibleDay = (item: RowItem, index: number): CalendarDay => ({ ...item.day, calendar_date: days[index].calendar_date });
  const totalCalories = days.reduce((sum, day) => sum + (day.has_plan ? number(day.plan_calories) ?? 0 : 0), 0);
  async function reorder(nextItems: RowItem[]) {
    setOptimistic({ signature, items: nextItems });
    try {
      await onReorder(days.map((day) => day.calendar_date), nextItems.map((item) => item.day.id));
    } catch {
      setOptimistic(null);
    }
  }
  function actions(item: RowItem, index: number) {
    const day = visibleDay(item, index);
    if (!day.has_plan) return [];
    return [
      { backgroundColor: "#515151", icon: <Pencil color={tokens.color.entityIconForeground} size={18} />, label: `Editar ${day.plan_name}`, onPress: () => onOpenDay(day) },
      ...(!day.has_execution ? [
        { backgroundColor: "#515151", icon: <RefreshCw color={tokens.color.entityIconForeground} size={18} />, label: `Reemplazar ${day.plan_name}`, onPress: () => onReplace(day) },
        { backgroundColor: "#DB294A", icon: <Trash2 color={tokens.color.entityIconForeground} size={18} />, label: `Eliminar ${day.plan_name}`, onPress: () => Alert.alert("Eliminar plan del calendario", `¿Quitar “${day.plan_name}” del ${dateLabel(day.calendar_date, { day: "numeric", month: "long" })}?`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void onRemove(day).catch(() => undefined) }]) },
      ] : []),
    ];
  }
  return <PanelSurface style={styles.surface}>
    <EntityPanelTabs activeTab={activeTab} onChange={setActiveTab} tabs={tabs} />
    <PanelBody>
      {activeTab !== "plans" ? <Header tab={activeTab} /> : null}
      <ComparisonPanelGestureRows
        actions={actions}
        canDrag={(item) => !item.day.has_execution}
        itemLabel={(item) => item.day.has_plan ? item.day.plan_name : "Fecha sin plan"}
        items={items}
        onReorder={reorder}
        renderRow={(item, index, onLongPress) => {
        const day = visibleDay(item, index);
        const calories = day.has_plan ? number(day.plan_calories) : null;
        const protein = day.has_plan ? number(day.plan_protein_grams) : null;
        const carbs = day.has_plan ? number(day.plan_carbs_grams) : null;
        const fat = day.has_plan ? number(day.plan_fat_grams) : null;
        const hasMacros = protein != null && carbs != null && fat != null && protein * 4 + carbs * 4 + fat * 9 > 0;
        const distribution = hasMacros ? macroCalorieShares({ proteinGrams: protein, carbsGrams: carbs, fatGrams: fat }) : null;
        return <Pressable
          accessibilityLabel={day.has_plan ? `Ver detalle de ${day.plan_name}` : `Asignar plan al ${dateLabel(day.calendar_date, { day: "numeric", month: "long" })}`}
          accessibilityRole="button"
          delayLongPress={320}
          onLongPress={onLongPress}
          onPress={() => runGuardedNavigation(() => onOpenDay(day))}
          style={[activeTab === "plans" ? styles.planRow : styles.analyticsRow, index === days.length - 1 && styles.lastRow]}>
          {activeTab === "plans" ? <>
            <PlanIdentity day={day} tab={activeTab} />
            <View style={styles.planCalories}>
              <Text style={styles.planCaloriesValue}>{integer(calories)}</Text>
              <Text style={styles.planCaloriesUnit}>kcal</Text>
            </View>
          </> : <>
            <View style={styles.leading}><PlanIdentity day={day} tab={activeTab} /></View>
            {activeTab === "calories" ? <>
              <Text style={[styles.value, styles.calorieCell]}>{integer(calories)}</Text>
              <View style={styles.shareCell}>{calories != null && totalCalories > 0
                ? <PanelAllocationBar tone="calories" value={calories / totalCalories * 100} />
                : <Text style={styles.emptyValue}>—</Text>}</View>
            </> : null}
            {activeTab === "macros" ? <>
              <View style={styles.ppkCell}>{number(day.plan_protein_per_kilogram) != null
                ? <ProteinPerKilogramBadge density="compact" showUnit={false} value={day.plan_protein_per_kilogram!} />
                : <Text style={styles.emptyValue}>—</Text>}</View>
              <Text style={[styles.value, styles.macroCell]}>{integer(protein)}</Text>
              <Text style={[styles.value, styles.macroCell]}>{integer(carbs)}</Text>
              <Text style={[styles.value, styles.macroCell]}>{integer(fat)}</Text>
            </> : null}
            {activeTab === "distribution" ? <>
              <Text style={[styles.value, styles.percentCell, styles.protein]}>{distribution ? `${distribution.protein}%` : "—"}</Text>
              <Text style={[styles.value, styles.percentCell, styles.carbs]}>{distribution ? `${distribution.carbs}%` : "—"}</Text>
              <Text style={[styles.value, styles.percentCell, styles.fat]}>{distribution ? `${distribution.fat}%` : "—"}</Text>
              <View style={styles.distributionCell}>{distribution
                ? <MacroCalorieDistribution proteinGrams={protein!} carbsGrams={carbs!} fatGrams={fat!} />
                : <Text style={styles.emptyValue}>—</Text>}</View>
            </> : null}
          </>}
        </Pressable>;
      }} visibleSwipeActions />
    </PanelBody>
  </PanelSurface>;
}

const styles = StyleSheet.create({
  surface: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen },
  planRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 68, paddingHorizontal: tokens.card.outerPadding, paddingVertical: tokens.spacing.sm },
  analyticsRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 62, paddingHorizontal: tokens.spacing.sm },
  lastRow: { borderBottomWidth: 0 },
  header: { minHeight: 32 },
  headerLabel: { color: tokens.color.textMuted, fontSize: 10, fontWeight: "600", textAlign: "center", textTransform: "uppercase" },
  leading: { flex: 4, minWidth: 0 },
  identity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.md, minWidth: 0 },
  dateColumn: { alignItems: "center", minWidth: 44 },
  dateWeekday: { color: tokens.color.textMuted, fontSize: 12 },
  dateNumber: { color: tokens.color.textMain, fontSize: 19, fontWeight: "700" },
  planCopy: { flex: 1, gap: 3, minWidth: 0 },
  planTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  planName: { color: tokens.color.textMain, flexShrink: 1, fontSize: 14, fontWeight: "600" },
  subtitle: { color: tokens.color.textMuted, fontSize: 11 },
  planCalories: { alignItems: "flex-end", minWidth: 62 },
  planCaloriesValue: { color: tokens.color.textMain, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: "700" },
  planCaloriesUnit: { color: tokens.color.textMuted, fontSize: 11 },
  value: { color: tokens.color.textMain, fontSize: 12, fontVariant: ["tabular-nums"], textAlign: "center" },
  emptyValue: { color: tokens.color.textMuted, fontSize: 12, textAlign: "center" },
  calorieCell: { flex: 1.2, minWidth: 0 },
  shareCell: { flex: 1.7, minWidth: 0 },
  ppkCell: { flex: 1, minWidth: 0 },
  macroCell: { flex: 0.75, minWidth: 0 },
  percentCell: { flex: 0.8, minWidth: 0 },
  distributionCell: { flex: 1.6, minWidth: 0 },
  protein: { color: tokens.color.protein, fontWeight: "600" },
  carbs: { color: tokens.color.carbs, fontWeight: "600" },
  fat: { color: tokens.color.fat, fontWeight: "600" },
  pressed: { opacity: 0.65 },
});
