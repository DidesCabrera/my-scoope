import { ChevronRight, CircleUserRound, MoreHorizontal } from "lucide-react-native";
import { Pressable, StyleProp, StyleSheet, Text, useWindowDimensions, View, ViewStyle } from "react-native";
import Svg, { Line, Polyline } from "react-native-svg";

import type { LibraryWeekPanelItem } from "@/api/types";
import { Card, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type ProgramMetricDatum = {
  allocation: { protein: number; carbs: number; fat: number };
  calories: number;
  carbs: number;
  fat: number;
  protein: number;
  ppk?: number | null;
};

type MetricRow = {
  key: "calories" | "ppk" | "protein" | "carbs" | "fat";
  label: string;
  range: string;
  color: string;
  values: number[];
};

const metricRows: MetricRow[] = [
  { key: "calories", label: "Calorías", range: "1840 - 2260 cal", color: "#764D35", values: [60, 82, 56, 88, 71, 66, 48, 74, 92, 62, 79, 69, 86, 53] },
  { key: "ppk", label: "PPK", range: "1,55 - 1,92 g/kg", color: tokens.color.ppk, values: [55, 76, 69, 87, 73, 82, 51, 70, 91, 64, 80, 75, 85, 58] },
  { key: "protein", label: "Proteína", range: "132 - 168 g", color: tokens.color.protein, values: [57, 78, 68, 90, 74, 84, 52, 72, 94, 63, 82, 77, 88, 56] },
  { key: "carbs", label: "Carbos", range: "196 - 254 g", color: tokens.color.carbs, values: [70, 91, 52, 84, 63, 72, 45, 87, 78, 58, 93, 67, 76, 49] },
  { key: "fat", label: "Grasas", range: "52 - 73 g", color: tokens.color.fat, values: [48, 66, 85, 59, 75, 51, 64, 81, 55, 73, 62, 89, 68, 47] },
];

const allocationValues = [
  [29, 46, 25], [31, 44, 25], [28, 48, 24], [30, 45, 25], [27, 47, 26], [32, 43, 25], [29, 49, 22],
  [30, 46, 24], [31, 45, 24], [28, 47, 25], [32, 44, 24], [29, 46, 25], [30, 48, 22], [31, 43, 26],
];

export function programDailyMetricData(weeks: LibraryWeekPanelItem[]): ProgramMetricDatum[] {
  return weeks.flatMap((week) => week.days.map((day) => ({
    allocation: {
      protein: day.nutrition?.protein.allocation ?? 0,
      carbs: day.nutrition?.carbs.allocation ?? 0,
      fat: day.nutrition?.fat.allocation ?? 0,
    },
    calories: day.nutrition?.calories ?? 0,
    protein: day.nutrition?.protein.grams ?? 0,
    carbs: day.nutrition?.carbs.grams ?? 0,
    fat: day.nutrition?.fat.grams ?? 0,
    ppk: day.nutrition?.protein.per_kilogram ?? null,
  })));
}

function liveRange(metric: MetricRow, values: number[] | undefined): string {
  const finite = (values ?? []).filter((value) => Number.isFinite(value) && value > 0);
  if (finite.length === 0) return metric.range;
  const minimum = Math.min(...finite);
  const maximum = Math.max(...finite);
  const unit = metric.key === "calories" ? "kcal" : metric.key === "ppk" ? "g/kg" : "g";
  const format = (value: number) => metric.key === "ppk" ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : Math.round(value).toLocaleString("es-CL");
  return `${format(minimum)} - ${format(maximum)} ${unit}`;
}

function ChartAxisHeader({ labels, metricColumnStyle }: { labels: string[]; metricColumnStyle: StyleProp<ViewStyle> }) {
  return (
    <View style={styles.weekHeader}>
      <View style={[styles.metricColumnSpacer, metricColumnStyle]} />
      <View accessibilityLabel="Eje del gráfico" style={styles.weekLabels}>
        {labels.map((label, index) => <Text key={`${index}-${label}`} style={styles.weekLabel}>{label}</Text>)}
      </View>
    </View>
  );
}

function MetricIdentity({ label, range, color, metricColumnStyle }: Pick<MetricRow, "label" | "range" | "color"> & { metricColumnStyle: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.metricIdentity, metricColumnStyle]}>
      <Text numberOfLines={1} style={styles.metricTitle}>{label}</Text>
      <Text numberOfLines={1} style={[styles.rangeBadge, { backgroundColor: color }, label !== "Calorías" && styles.rangeBadgeDarkText]}>{range}</Text>
    </View>
  );
}

function MetricPlot({ days, metric, values: providedValues }: { days: number; metric: MetricRow; values?: number[] }) {
  const rawValues = (providedValues ?? metric.values).slice(0, days);
  const maximum = Math.max(...rawValues, 1);
  const values = providedValues ? rawValues.map((value) => 12 + (value / maximum) * 82) : rawValues;
  const divisor = Math.max(values.length - 1, 1);
  const coordinates = values.map((value, index) => ({ x: index * (140 / divisor), y: 43 - value * 0.4 }));
  const points = coordinates.map(({ x, y }) => `${x},${y}`).join(" ");
  return (
    <View accessibilityLabel={`${metric.label}: ${metric.range}`} style={styles.metricPlot}>
      <Svg height="100%" preserveAspectRatio="none" viewBox="0 0 140 44" width="100%">
        <Line stroke={tokens.color.borderSoft} strokeWidth="0.8" x1="70" x2="70" y1="0" y2="44" />
        <Polyline fill="none" points={points} stroke={metric.color} strokeLinejoin="round" strokeLinecap="round" strokeWidth="2.6" vectorEffect="non-scaling-stroke" />
        {coordinates.map(({ x, y }, index) => <Line key={`${metric.key}-point-${index}`} stroke={metric.color} strokeLinecap="round" strokeWidth="5" vectorEffect="non-scaling-stroke" x1={x} x2={x} y1={y} y2={y} />)}
      </Svg>
    </View>
  );
}

function AllocationPlot({ days, values = allocationValues }: { days: number; values?: number[][] }) {
  return (
    <View accessibilityLabel="Distribución de macronutrientes por día" style={[styles.metricPlot, styles.allocationPlot]}>
      {values.slice(0, days).map(([protein, carbs, fat], index) => {
        const hasAllocation = protein + carbs + fat > 0;
        return (
          <View key={`allocation-${index}`} style={[styles.allocationSlot, days > 7 && index === 7 && styles.weekDivider]}>
            {hasAllocation ? <>
              <View style={[styles.allocationSegment, { backgroundColor: tokens.color.protein, flex: protein }]} />
              <View style={[styles.allocationSegment, { backgroundColor: tokens.color.carbs, flex: carbs }]} />
              <View style={[styles.allocationSegment, { backgroundColor: tokens.color.fat, flex: fat }]} />
            </> : null}
          </View>
        );
      })}
    </View>
  );
}

function allocationRange(values: number[][] | undefined, index: number, fallback: string): string {
  const finite = (values ?? []).map((row) => row[index]).filter((value) => Number.isFinite(value) && value > 0);
  if (!finite.length) return fallback;
  return `${Math.round(Math.min(...finite))} - ${Math.round(Math.max(...finite))}%`;
}

export function ProgramMetricPreview({
  axisLabels = ["S1", "S2"],
  data,
  days = 14,
  style,
}: {
  axisLabels?: string[];
  data?: ProgramMetricDatum[];
  days?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const { width } = useWindowDimensions();
  const metricColumnStyle = width <= 780
    ? { width: 120 }
    : { minWidth: 92, width: "24%" as const };

  const metricValues: Record<MetricRow["key"], number[]> | undefined = data ? {
    calories: data.map((item) => item.calories),
    ppk: data.map((item) => item.ppk ?? 0),
    protein: data.map((item) => item.protein),
    carbs: data.map((item) => item.carbs),
    fat: data.map((item) => item.fat),
  } : undefined;
  const liveAllocationValues = data?.map(({ allocation }) => [allocation.protein, allocation.carbs, allocation.fat]);

  return (
    <View accessibilityLabel="Gráficos de KPI del programa" style={[styles.chartPreview, style]}>
      <ChartAxisHeader labels={axisLabels} metricColumnStyle={metricColumnStyle} />
      {metricRows.map((metric) => (
        <View key={metric.key} style={styles.metricRow}>
          <MetricIdentity color={metric.color} label={metric.label} metricColumnStyle={metricColumnStyle} range={liveRange(metric, metricValues?.[metric.key])} />
          <MetricPlot days={days} metric={metric} values={metricValues?.[metric.key]} />
        </View>
      ))}
      <View style={styles.metricRow}>
        <View style={[styles.metricIdentity, styles.allocationIdentity, metricColumnStyle]}>
          <Text style={styles.metricTitle}>Alloc</Text>
          <View style={styles.allocationRanges}>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.protein }]}>P {allocationRange(liveAllocationValues, 0, "27 - 32%")}</Text>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.carbs }]}>C {allocationRange(liveAllocationValues, 1, "43 - 49%")}</Text>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.fat }]}>G {allocationRange(liveAllocationValues, 2, "22 - 26%")}</Text>
          </View>
        </View>
        <AllocationPlot days={days} values={liveAllocationValues} />
      </View>
    </View>
  );
}

export function ProgramChildCard({
  title,
  weeksCount,
  filledDaysCount,
  foodsCount,
  owner,
  onOpen,
  onMore,
  metricData,
  axisLabels,
}: {
  title: string;
  weeksCount: number;
  filledDaysCount: number;
  foodsCount: number;
  owner: string;
  onOpen(): void;
  onMore(): void;
  metricData?: ProgramMetricDatum[];
  axisLabels?: string[];
}) {
  return (
    <Card accent={tokens.color.program}>
      <EntityHeading
        entity="program"
        indicators={[
          { label: "semanas", value: `${weeksCount} SEMANAS` },
          { icon: "dailyPlan", label: "planes asignados", value: filledDaysCount },
          { icon: "food", label: "alimentos", value: foodsCount },
        ]}
        title={title}
      />

      <ProgramMetricPreview axisLabels={axisLabels} data={metricData} days={metricData?.length ?? 14} />

      <View style={styles.footer}>
        <View accessibilityLabel={`Creado por ${owner}`} style={styles.owner}>
          <CircleUserRound color={tokens.color.textMuted} size={17} />
          <Text style={styles.ownerText}>{owner}</Text>
        </View>
        <View style={styles.actions}>
          <Pressable accessibilityLabel="Más acciones" accessibilityRole="button" onPress={onMore} style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}>
            <MoreHorizontal color={tokens.color.textMuted} size={21} />
          </Pressable>
          <Pressable accessibilityLabel="Ver programa" accessibilityRole="button" onPress={onOpen} style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}>
            <ChevronRight color={tokens.color.textMuted} size={21} />
          </Pressable>
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.62 },
  chartPreview: { gap: tokens.spacing.compact, marginTop: tokens.spacing.sm },
  weekHeader: { flexDirection: "row" },
  metricColumnSpacer: { flexGrow: 0, flexShrink: 0 },
  weekLabels: { flex: 1, flexDirection: "row", gap: 2, paddingHorizontal: tokens.spacing.compact },
  weekLabel: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, color: tokens.color.textMain, flex: 1, fontSize: 10, fontWeight: "700", minHeight: 18, paddingTop: 3, textAlign: "center" },
  metricRow: { alignItems: "stretch", flexDirection: "row", minWidth: 0 },
  metricIdentity: { alignContent: "center", backgroundColor: tokens.color.surfaceMuted, borderBottomLeftRadius: tokens.radius.md, borderTopLeftRadius: tokens.radius.md, flexGrow: 0, flexShrink: 0, gap: tokens.spacing.xs, justifyContent: "center", paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.compact },
  metricTitle: { color: tokens.color.textMain, fontSize: 14, fontWeight: "600", lineHeight: 16 },
  rangeBadge: { alignSelf: "flex-start", borderRadius: tokens.radius.sm, color: tokens.color.textMain, fontSize: 11, fontVariant: ["tabular-nums"], fontWeight: "600", maxWidth: "100%", overflow: "hidden", paddingHorizontal: tokens.spacing.compact, paddingVertical: 2 },
  rangeBadgeDarkText: { color: tokens.color.surfaceApp },
  metricPlot: { borderColor: tokens.color.surfaceMuted, borderTopRightRadius: tokens.radius.md, borderBottomRightRadius: tokens.radius.md, borderWidth: 1, flex: 1, height: 58, minWidth: 0, overflow: "hidden", paddingHorizontal: tokens.spacing.compact, paddingVertical: tokens.spacing.compact },
  allocationIdentity: { paddingVertical: tokens.spacing.sm },
  allocationRanges: { alignItems: "flex-start", gap: 3 },
  allocationRange: { borderRadius: tokens.radius.sm, color: tokens.color.surfaceApp, fontSize: 10, fontVariant: ["tabular-nums"], fontWeight: "700", overflow: "hidden", paddingHorizontal: tokens.spacing.compact, paddingVertical: 1 },
  allocationPlot: { alignItems: "stretch", flexDirection: "row", height: 94, paddingHorizontal: tokens.spacing.compact, paddingVertical: tokens.spacing.sm },
  allocationSlot: { flex: 1, flexDirection: "column-reverse", gap: 2, minWidth: 0, paddingHorizontal: 1 },
  allocationSegment: { borderRadius: 2, minHeight: 1 },
  weekDivider: { borderLeftColor: tokens.color.borderSoft, borderLeftWidth: 1 },
  footer: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", justifyContent: "space-between", marginTop: tokens.spacing.sm, paddingTop: tokens.spacing.md },
  owner: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  ownerText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "600" },
  actions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  actionButton: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
});
