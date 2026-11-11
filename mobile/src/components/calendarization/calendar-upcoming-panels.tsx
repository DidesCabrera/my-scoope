import { useId, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import type { CalendarDay } from "@/api/types";
import { MacroCalorieDistribution, macroCalorieShares, ProteinPerKilogramBadge } from "@/components/nutrition";
import { EntityPanelTabs, PanelBody, PanelSurface } from "@/components/panels";
import { ComparisonPanelGestureRows } from "@/components/libraries/comparison-panel-gesture-rows";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { runGuardedNavigation } from "@/navigation/navigation-press-guard";

type Tab = "plans" | "macros" | "distribution";

const tabs = [
  { key: "plans", label: "Minutas" },
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

function TodayIndicator() {
  const gradientId = useId().replace(/:/g, "");
  return <View pointerEvents="none" style={styles.todayIndicator}>
    <Svg height={3} width={22}>
      <Defs>
        <LinearGradient id={gradientId} x1="0%" x2="100%" y1="0%" y2="0%">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.5" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      <Rect fill={`url(#${gradientId})`} height={3} rx={1.5} width={22} />
    </Svg>
  </View>;
}

function PlanIdentity({ day, isToday, muted = false, tab }: { day: CalendarDay; isToday: boolean; muted?: boolean; tab: Tab }) {
  const icon = day.has_plan ? <EntityIcon entity="dailyPlan" size="compact" /> : <View style={styles.emptyPlanIcon}><Text style={styles.emptyPlanIconLabel}>—</Text></View>;
  return (
    <View style={[styles.identity, muted && styles.pastContent]}>
      {tab === "plans" ? <View style={styles.dateColumn}>
        <Text style={styles.dateWeekday}>{dateLabel(day.calendar_date, { weekday: "short" })}</Text>
        <Text style={styles.dateNumber}>{day.calendar_date.slice(8, 10)}</Text>
        <View style={styles.todayIndicatorSlot}>{isToday ? <TodayIndicator /> : null}</View>
      </View> : null}
      <View style={styles.planCopy}>
        <View style={styles.planTitleRow}>
          {tab === "plans" ? icon : <View style={[styles.analyticsIcon, isToday && styles.analyticsIconWithTodayIndicator]}>
            {icon}
            {isToday ? <View style={styles.analyticsTodayIndicator}><TodayIndicator /></View> : null}
          </View>}
          <Text numberOfLines={2} style={[styles.planName, !day.has_plan && styles.planNameEmpty]}>{day.has_plan ? day.plan_name : "Sin minuta"}</Text>
        </View>
        {tab === "plans" && day.has_plan && day.source_program_name
          ? <Text numberOfLines={1} style={styles.subtitle}>{day.source_program_name}</Text>
          : null}
      </View>
    </View>
  );
}

function Header({ tab }: { tab: Exclude<Tab, "plans"> }) {
  return <View style={[styles.analyticsRow, styles.header]}>
    <Text style={[styles.headerLabel, styles.leading, styles.leadingHeader]}>Minutas diarias</Text>
    {tab === "macros" ? <>
      <Text style={[styles.headerLabel, styles.macroMetricCell]}>P</Text>
      <Text style={[styles.headerLabel, styles.macroMetricCell]}>PpK</Text>
      <Text style={[styles.headerLabel, styles.macroMetricCell]}>C</Text>
      <Text style={[styles.headerLabel, styles.macroMetricCell]}>G</Text>
    </> : null}
    {tab === "distribution" ? <>
      <Text style={[styles.headerLabel, styles.percentCell]}>P%</Text>
      <Text style={[styles.headerLabel, styles.percentCell]}>C%</Text>
      <Text style={[styles.headerLabel, styles.percentCell]}>G%</Text>
      <Text style={[styles.headerLabel, styles.distributionCell]}>P|C|G</Text>
    </> : null}
  </View>;
}

type RowItem = { id: string; day: CalendarDay };

export function CalendarUpcomingPanels({ days, localDate, onAssign, onOpenDay, onRemove, onReorder, onReplace, weightKg }: {
  days: CalendarDay[];
  localDate: string;
  onAssign(day: CalendarDay): void;
  onOpenDay(day: CalendarDay): void;
  onRemove(day: CalendarDay): Promise<void>;
  onReorder(dates: string[], orderedDayIds: (number | null)[]): Promise<void>;
  onReplace(day: CalendarDay): void;
  weightKg: number | null;
}) {
  const [requestedTab, setActiveTab] = useState<Tab>("plans");
  const activeTab = requestedTab === "macros" || requestedTab === "distribution" ? requestedTab : "plans";
  const [optimistic, setOptimistic] = useState<{ signature: string; items: RowItem[] } | null>(null);
  const signature = days.map((day) => `${day.calendar_date}:${day.id ?? "empty"}`).join("|");
  const sourceItems = days.map((day) => ({ id: day.id == null ? `empty-${day.calendar_date}` : `plan-${day.id}`, day }));
  const items = optimistic?.signature === signature ? optimistic.items : sourceItems;
  const visibleDay = (item: RowItem, index: number): CalendarDay => ({ ...item.day, calendar_date: days[index].calendar_date });
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
  return <View style={styles.section}>
    <View style={styles.tabsBleed}><EntityPanelTabs activeTab={activeTab} contentContainerStyle={styles.tabs} onChange={setActiveTab} tabs={tabs} /></View>
    <PanelSurface style={styles.surface}>
    <PanelBody style={[styles.tableBody, activeTab !== "plans" && styles.analyticsTableBody]}>
      {activeTab !== "plans" ? <Header tab={activeTab} /> : null}
      <ComparisonPanelGestureRows
        actions={actions}
        canDrag={(item) => !item.day.has_execution}
        itemLabel={(item) => item.day.has_plan ? item.day.plan_name : "Fecha sin minuta"}
        items={items}
        onReorder={reorder}
        renderRow={(item, index, onLongPress) => {
        const day = visibleDay(item, index);
        const calories = day.has_plan ? number(day.plan_calories) : null;
        const protein = day.has_plan ? number(day.plan_protein_grams) : null;
        const ppk = protein != null && weightKg != null && Number.isFinite(weightKg) && weightKg > 0
          ? protein / weightKg : null;
        const carbs = day.has_plan ? number(day.plan_carbs_grams) : null;
        const fat = day.has_plan ? number(day.plan_fat_grams) : null;
        const hasMacros = protein != null && carbs != null && fat != null && protein * 4 + carbs * 4 + fat * 9 > 0;
        const distribution = hasMacros ? macroCalorieShares({ proteinGrams: protein, carbsGrams: carbs, fatGrams: fat }) : null;
        const isPast = day.calendar_date < localDate;
        return <Pressable
          accessibilityLabel={`${day.calendar_date === localDate ? "Hoy: " : ""}${day.has_plan ? `Ver detalle de ${day.plan_name}` : `Ver el ${dateLabel(day.calendar_date, { day: "numeric", month: "long" })} sin minuta`}`}
          accessibilityRole="button"
          delayLongPress={320}
          onLongPress={onLongPress}
          onPress={() => runGuardedNavigation(() => onOpenDay(day))}
          style={[activeTab === "plans" ? styles.planRow : styles.analyticsRow, index === days.length - 1 && styles.lastRow, isPast && styles.pastBackground]}>
          {activeTab === "plans" ? <>
            <PlanIdentity day={day} isToday={day.calendar_date === localDate} muted={isPast} tab={activeTab} />
            {day.has_plan ? <View style={[styles.planCalories, isPast && styles.pastContent]}>
              <Text style={styles.planCaloriesValue}>{integer(calories)}</Text>
              <Text style={styles.planCaloriesUnit}>kcal</Text>
            </View> : <Pressable accessibilityLabel={`Asignar minuta al ${dateLabel(day.calendar_date, { day: "numeric", month: "long" })}`} accessibilityRole="button" onPress={(event) => { event.stopPropagation(); onAssign(day); }} style={({ pressed }) => [styles.assignChip, isPast && styles.pastContent, pressed && styles.pressed]}>
              <Plus color={tokens.color.textMain} size={15} strokeWidth={2.2} />
              <Text style={styles.assignChipLabel}>Asignar minuta</Text>
            </Pressable>}
          </> : <>
            <View style={[styles.leading, isPast && styles.pastContent]}><PlanIdentity day={day} isToday={day.calendar_date === localDate} tab={activeTab} /></View>
            {activeTab === "macros" ? <>
              <Text style={[styles.value, styles.macroMetricCell, isPast && styles.pastContent]}>{integer(protein)}</Text>
              <View style={[styles.macroMetricCell, isPast && styles.pastContent]}>{ppk != null
                ? <ProteinPerKilogramBadge density="compact" showUnit={false} style={styles.ppkBadge} value={ppk} />
                : <Text style={styles.emptyValue}>—</Text>}</View>
              <Text style={[styles.value, styles.macroMetricCell, isPast && styles.pastContent]}>{integer(carbs)}</Text>
              <Text style={[styles.value, styles.macroMetricCell, isPast && styles.pastContent]}>{integer(fat)}</Text>
            </> : null}
            {activeTab === "distribution" ? <>
              <Text style={[styles.value, styles.percentCell, styles.protein, isPast && styles.pastContent]}>{distribution ? `${distribution.protein}%` : "—"}</Text>
              <Text style={[styles.value, styles.percentCell, styles.carbs, isPast && styles.pastContent]}>{distribution ? `${distribution.carbs}%` : "—"}</Text>
              <Text style={[styles.value, styles.percentCell, styles.fat, isPast && styles.pastContent]}>{distribution ? `${distribution.fat}%` : "—"}</Text>
              <View style={[styles.distributionCell, isPast && styles.pastContent]}>{distribution
                ? <MacroCalorieDistribution proteinGrams={protein!} carbsGrams={carbs!} fatGrams={fat!} />
                : <Text style={styles.emptyValue}>—</Text>}</View>
            </> : null}
          </>}
        </Pressable>;
      }} visibleSwipeActions />
    </PanelBody>
    </PanelSurface>
  </View>;
}

const styles = StyleSheet.create({
  section: { gap: 0 },
  tabs: { paddingLeft: 0 },
  tabsBleed: { marginHorizontal: -9 },
  tableBody: { borderTopWidth: 0 },
  analyticsTableBody: { paddingTop: 4 },
  surface: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen },
  assignChip: { alignItems: "center", backgroundColor: `${tokens.color.dailyPlan}1A`, borderColor: tokens.color.dailyPlan, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: 4, marginRight: -6, minHeight: 30, paddingHorizontal: 9 },
  assignChipLabel: { color: tokens.color.textMain, fontSize: 12, fontWeight: "600" },
  planRow: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 68, paddingLeft: tokens.card.outerPadding - 10, paddingRight: tokens.card.outerPadding, paddingVertical: tokens.spacing.sm },
  analyticsRow: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, columnGap: tokens.spacing.sm, flexDirection: "row", minHeight: 60, paddingLeft: tokens.spacing.md, paddingRight: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  lastRow: { borderBottomWidth: 0 },
  pastBackground: { backgroundColor: `${tokens.color.surfaceApp}80` },
  pastContent: { opacity: 0.35 },
  header: { minHeight: 32, paddingVertical: 0 },
  headerLabel: { color: tokens.color.textMuted, fontSize: 10, fontWeight: "600", textAlign: "center", textTransform: "uppercase" },
  leadingHeader: { textAlign: "left" },
  leading: { flexBasis: "38%", flexGrow: 0, flexShrink: 0, minWidth: 0 },
  identity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  dateColumn: { alignItems: "center", height: 46, justifyContent: "center", minWidth: 44, width: 44 },
  dateWeekday: { color: tokens.color.textMuted, fontSize: 12, lineHeight: 14 },
  dateNumber: { color: tokens.color.textMain, fontSize: 19, fontWeight: "700", lineHeight: 22 },
  todayIndicatorSlot: { height: 7, justifyContent: "flex-end" },
  todayIndicator: { height: 3, width: 22 },
  planCopy: { flex: 1, gap: 3, minWidth: 0 },
  planTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  analyticsIcon: { height: 18, width: 18 },
  analyticsIconWithTodayIndicator: { height: 29 },
  analyticsTodayIndicator: { left: -2, position: "absolute", top: 26 },
  emptyPlanIcon: { alignItems: "center", height: 18, justifyContent: "center", width: 18 },
  emptyPlanIconLabel: { color: tokens.color.textMuted, fontSize: 14 },
  planName: { color: tokens.color.textMain, flexShrink: 1, fontSize: 14, fontWeight: "600" },
  planNameEmpty: { color: tokens.color.textMuted, fontWeight: "400" },
  subtitle: { color: tokens.color.textMuted, fontSize: 11 },
  planCalories: { alignItems: "flex-end", minWidth: 62 },
  planCaloriesValue: { color: tokens.color.textMain, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: "700" },
  planCaloriesUnit: { color: tokens.color.textMuted, fontSize: 11 },
  value: { color: tokens.color.textMain, fontSize: 12, fontVariant: ["tabular-nums"], textAlign: "center" },
  emptyValue: { color: tokens.color.textMuted, fontSize: 12, textAlign: "center" },
  macroMetricCell: { flex: 1, minWidth: 0 },
  ppkBadge: { height: 24, minHeight: 24 },
  percentCell: { flex: 0.8, minWidth: 0 },
  distributionCell: { flex: 1.6, minWidth: 0 },
  protein: { color: tokens.color.protein, fontWeight: "600" },
  carbs: { color: tokens.color.carbs, fontWeight: "600" },
  fat: { color: tokens.color.fat, fontWeight: "600" },
  pressed: { opacity: 0.65 },
});
