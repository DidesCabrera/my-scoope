import { ChevronRight, MoreHorizontal } from "lucide-react-native";
import { Pressable, ScrollView, StyleProp, StyleSheet, Text, useWindowDimensions, View, ViewStyle } from "react-native";
import { useState } from "react";
import Svg, { Defs, Line, LinearGradient, Polygon, Polyline, Rect, Stop } from "react-native-svg";

import type { LibraryNutrition } from "@/api/types";
import { Card, EntityCardAction, EntityCardActions, EntityCardPanelToggle, EntityHeading, type EntityHeadingLink, layoutStyles } from "@/components/ui";
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
  unit: "kcal" | "g/kg" | "g";
  values: number[];
};

const metricRows: MetricRow[] = [
  { key: "calories", label: "Calorías", range: "1840 - 2260 cal", color: tokens.color.kcalBorder, unit: "kcal", values: [60, 82, 56, 88, 71, 66, 48, 74, 92, 62, 79, 69, 86, 53] },
  { key: "ppk", label: "PPK", range: "1,55 - 1,92 g/kg", color: tokens.color.ppk, unit: "g/kg", values: [55, 76, 69, 87, 73, 82, 51, 70, 91, 64, 80, 75, 85, 58] },
  { key: "protein", label: "Proteína", range: "132 - 168 g", color: tokens.color.protein, unit: "g", values: [57, 78, 68, 90, 74, 84, 52, 72, 94, 63, 82, 77, 88, 56] },
  { key: "carbs", label: "Carbos", range: "196 - 254 g", color: tokens.color.carbs, unit: "g", values: [70, 91, 52, 84, 63, 72, 45, 87, 78, 58, 93, 67, 76, 49] },
  { key: "fat", label: "Grasas", range: "52 - 73 g", color: tokens.color.fat, unit: "g", values: [48, 66, 85, 59, 75, 51, 64, 81, 55, 73, 62, 89, 68, 47] },
];

const allocationValues = [
  [29, 46, 25], [31, 44, 25], [28, 48, 24], [30, 45, 25], [27, 47, 26], [32, 43, 25], [29, 49, 22],
  [30, 46, 24], [31, 45, 24], [28, 47, 25], [32, 44, 24], [29, 46, 25], [30, 48, 22], [31, 43, 26],
];

export function programDailyMetricData(weeks: { days: { nutrition?: LibraryNutrition | null }[] }[]): ProgramMetricDatum[] {
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
  if (finite.length === 0) return values ? "Sin datos" : metric.range;
  const minimum = Math.min(...finite);
  const maximum = Math.max(...finite);
  const unit = metric.key === "calories" ? "kcal" : metric.key === "ppk" ? "g/kg" : "g";
  const format = (value: number) => metric.key === "ppk" ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : Math.round(value).toLocaleString("es-CL");
  return `${format(minimum)} - ${format(maximum)} ${unit}`;
}

function programWeekRangeLabel(labels: string[]): string {
  const weekNumbers = labels
    .map((label) => Number.parseInt(label.replace(/^S/i, ""), 10))
    .filter((week) => Number.isFinite(week) && week > 0);
  const lastWeek = weekNumbers.length ? Math.max(...weekNumbers) : 1;
  return lastWeek === 1 ? "Semana 1" : `Semanas 1-${lastWeek}`;
}

function ChartAxisLabels({ labels }: { labels: string[] }) {
  return (
    <View accessibilityLabel="Eje del gráfico" style={styles.weekLabels}>
      {labels.map((label, index) => (
        <View key={`${index}-${label}`} style={styles.weekLabelCell}>
          <Text style={[styles.axisChip, styles.weekLabel]}>{label}</Text>
        </View>
      ))}
    </View>
  );
}

function MetricIdentity({ metricKey, label, range, color }: Pick<MetricRow, "label" | "range" | "color"> & { metricKey: MetricRow["key"] }) {
  const isCalories = metricKey === "calories";
  return (
    <View style={styles.metricIdentity}>
      <Text numberOfLines={1} style={styles.metricTitle}>{label}</Text>
      <Text
        numberOfLines={1}
        style={[
          styles.rangeBadge,
          isCalories ? styles.rangeBadgeCalories : { backgroundColor: color },
          !isCalories && styles.rangeBadgeDarkText,
        ]}>
        {range}
      </Text>
    </View>
  );
}

function InlineDayLabels({ labels }: { labels: string[] }) {
  return (
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" pointerEvents="none" style={styles.inlineDayLabels}>
      {labels.map((label, index) => <Text key={`${label}-${index}`} style={styles.inlineDayLabel}>{label}</Text>)}
    </View>
  );
}

function AllocationSegment({ color, fullWidth, id, value }: { color: string; fullWidth: boolean; id: string; value: number }) {
  return (
    <View style={[styles.allocationSegment, { backgroundColor: fullWidth ? "transparent" : color, flex: value }, fullWidth && styles.weekAllocationSegment]}>
      {fullWidth ? (
        <Svg height="100%" pointerEvents="none" preserveAspectRatio="none" style={StyleSheet.absoluteFill} width="100%">
          <Defs>
            <LinearGradient id={id} x1="0" x2="0" y1="0" y2="1">
              <Stop offset="0" stopColor={color} stopOpacity={1} />
              <Stop offset="1" stopColor={color} stopOpacity={0.8} />
            </LinearGradient>
          </Defs>
          <Rect fill={`url(#${id})`} height="100%" width="100%" x="0" y="0" />
        </Svg>
      ) : null}
      {fullWidth ? <Text numberOfLines={1} style={styles.allocationSegmentLabel}>{Math.round(value)}%</Text> : null}
    </View>
  );
}

function MetricPlot({ axisLabels, days, fullWidth = false, metric, values: providedValues }: { axisLabels?: string[]; days: number; fullWidth?: boolean; metric: MetricRow; values?: number[] }) {
  const [renderedSize, setRenderedSize] = useState({ height: 116, width: 320 });
  const rawValues = (providedValues ?? metric.values).slice(0, days);
  const maximum = Math.max(...rawValues, 1);
  const values = providedValues ? rawValues.map((value) => 12 + (value / maximum) * 82) : rawValues;
  const slotCount = Math.max(values.length, 1);
  const plotHeight = fullWidth ? 84 : 44;
  const plotBaseline = fullWidth ? 66 : 44;
  const coordinates = values.map((value, index) => ({
    x: (index + 0.5) * (140 / slotCount),
    y: fullWidth ? 62 - value * 0.3 : 43 - value * 0.4,
  }));
  const weekDividers = Array.from(
    { length: Math.max(0, Math.ceil(values.length / 7) - 1) },
    (_, index) => (index + 1) * 7 * (140 / slotCount),
  );
  const points = coordinates.map(({ x, y }) => `${x},${y}`).join(" ");
  const barWidth = Math.max(1, (140 / slotCount) - 1);
  const barCornerRadius = 8;
  const barRadiusX = barCornerRadius * 140 / renderedSize.width;
  const barRadiusY = barCornerRadius * plotHeight / renderedSize.height;
  const areaPoints = coordinates.length > 1
    ? `${coordinates[0].x},${plotBaseline} ${points} ${coordinates[coordinates.length - 1].x},${plotBaseline}`
    : "";
  const formatPointValue = (value: number) => metric.key === "ppk"
    ? value.toLocaleString("es-CL", { maximumFractionDigits: 1 })
    : Math.round(value).toLocaleString("es-CL");
  return (
    <View
      accessibilityLabel={`${metric.label}: ${providedValues ? liveRange(metric, providedValues) : metric.range}`}
      onLayout={fullWidth ? ({ nativeEvent }) => setRenderedSize(nativeEvent.layout) : undefined}
      style={[styles.metricPlot, fullWidth && styles.weekFullWidthPlot, fullWidth && styles.weekMetricPlot]}>
      {fullWidth ? <Text style={styles.inlineChartTitle}>{metric.label}</Text> : null}
      {fullWidth ? <Text style={styles.inlineChartUnit}>{metric.unit}</Text> : null}
      <Svg height="100%" preserveAspectRatio="none" viewBox={`0 0 140 ${plotHeight}`} width="100%">
        <Defs>
          <LinearGradient gradientUnits="userSpaceOnUse" id={`metric-area-${metric.key}`} x1="0" x2="0" y1="0" y2={plotHeight}>
            <Stop offset="0" stopColor={metric.color} stopOpacity={0.44} />
            <Stop offset="1" stopColor={metric.color} stopOpacity={0} />
          </LinearGradient>
          <LinearGradient id={`metric-bar-${metric.key}`} x1="0" x2="0" y1="0" y2="1">
            <Stop offset="0" stopColor={metric.color} stopOpacity={1} />
            <Stop offset="1" stopColor={metric.color} stopOpacity={0.5} />
          </LinearGradient>
        </Defs>
        {weekDividers.map((x, index) => <Line key={`week-divider-${index}`} stroke={tokens.color.borderSoft} strokeWidth="0.8" x1={x} x2={x} y1="0" y2={plotHeight} />)}
        {fullWidth ? coordinates.map(({ x, y }, index) => rawValues[index] > 0 ? (
          <Rect
            fill={`url(#metric-bar-${metric.key})`}
            height={Math.max(1, plotBaseline - y)}
            key={`${metric.key}-bar-${index}`}
            rx={barRadiusX}
            ry={barRadiusY}
            width={barWidth}
            x={x - barWidth / 2}
            y={y}
          />
        ) : null) : (
          <>
            {areaPoints ? <Polygon fill={`url(#metric-area-${metric.key})`} points={areaPoints} /> : null}
            <Polyline fill="none" points={points} stroke={metric.color} strokeLinejoin="round" strokeLinecap="round" strokeWidth="2" vectorEffect="non-scaling-stroke" />
            {coordinates.map(({ x, y }, index) => <Line key={`${metric.key}-point-${index}`} stroke={metric.color} strokeLinecap="round" strokeWidth="3" vectorEffect="non-scaling-stroke" x1={x} x2={x} y1={y} y2={y} />)}
          </>
        )}
      </Svg>
      {fullWidth ? (
        <View pointerEvents="none" style={styles.pointLabels}>
          {coordinates.map(({ y }, index) => (
            <Text
              key={`${metric.key}-value-${index}`}
              numberOfLines={1}
              style={[
                styles.pointLabel,
                {
                  left: `${((index + 0.5) / slotCount) * 100}%`,
                  top: `${Math.max(0, (y / plotHeight) * 100 - 12)}%`,
                },
              ]}>
              {rawValues[index] > 0 ? formatPointValue(rawValues[index]) : "—"}
            </Text>
          ))}
        </View>
      ) : null}
      {fullWidth && axisLabels ? <InlineDayLabels labels={axisLabels.slice(0, days)} /> : null}
    </View>
  );
}

function AllocationPlot({ axisLabels, days, fullWidth = false, values = allocationValues }: { axisLabels?: string[]; days: number; fullWidth?: boolean; values?: number[][] }) {
  return (
    <View accessibilityLabel="Distribución de macronutrientes por día" style={[styles.metricPlot, styles.allocationPlot, fullWidth && styles.weekFullWidthPlot, fullWidth && styles.weekAllocationPlot]}>
      {fullWidth ? <Text style={styles.inlineChartTitle}>Alloc</Text> : null}
      {fullWidth ? <Text style={styles.inlineChartUnit}>%</Text> : null}
      {values.slice(0, days).map(([protein, carbs, fat], index) => {
        const hasAllocation = protein + carbs + fat > 0;
        return (
          <View key={`allocation-${index}`} style={[styles.allocationSlot, index > 0 && index % 7 === 0 && styles.weekDivider]}>
            {hasAllocation ? <>
              <AllocationSegment color={tokens.color.protein} fullWidth={fullWidth} id={`allocation-protein-${index}`} value={protein} />
              <AllocationSegment color={tokens.color.carbs} fullWidth={fullWidth} id={`allocation-carbs-${index}`} value={carbs} />
              <AllocationSegment color={tokens.color.fat} fullWidth={fullWidth} id={`allocation-fat-${index}`} value={fat} />
            </> : null}
          </View>
        );
      })}
      {fullWidth && axisLabels ? <InlineDayLabels labels={axisLabels.slice(0, days)} /> : null}
    </View>
  );
}

function allocationRange(values: number[][] | undefined, index: number, fallback: string): string {
  const finite = (values ?? []).map((row) => row[index]).filter((value) => Number.isFinite(value) && value > 0);
  if (!finite.length) return fallback;
  return `${Math.round(Math.min(...finite))} - ${Math.round(Math.max(...finite))}%`;
}

type MetricPreviewProps = {
  axisLeadingLabel?: string;
  axisLabels?: string[];
  data?: ProgramMetricDatum[];
  days?: number;
  style?: StyleProp<ViewStyle>;
};

export type WeekMetricFilter = "all" | "calories" | "ppk" | "macros" | "allocation";

function MetricPreview({
  axisLeadingLabel,
  axisLabels = ["S1", "S2"],
  data,
  days = 14,
  filter = "all",
  scope,
  style,
}: MetricPreviewProps & { filter?: WeekMetricFilter; scope: "program" | "week" }) {
  const { width } = useWindowDimensions();
  const [plotViewportWidth, setPlotViewportWidth] = useState(0);
  const metricColumnStyle = width < 600
    ? { width: "40%" as const }
    : { minWidth: 132, width: "24%" as const };
  const chartContentWidth = plotViewportWidth
    ? plotViewportWidth * Math.max(1, axisLabels.length / 8)
    : undefined;

  const metricValues: Record<MetricRow["key"], number[]> | undefined = data ? {
    calories: data.map((item) => item.calories),
    ppk: data.map((item) => item.ppk ?? 0),
    protein: data.map((item) => item.protein),
    carbs: data.map((item) => item.carbs),
    fat: data.map((item) => item.fat),
  } : undefined;
  const liveAllocationValues = data?.map(({ allocation }) => [allocation.protein, allocation.carbs, allocation.fat]);

  if (scope === "week") {
    const visibleMetrics = filter === "all"
      ? metricRows
      : filter === "macros"
        ? metricRows.filter(({ key }) => key === "protein" || key === "carbs" || key === "fat")
        : metricRows.filter(({ key }) => key === filter);
    const showAllocation = filter === "all" || filter === "allocation";
    return (
      <View accessibilityLabel="Gráficos de KPI de la semana" style={[styles.chartPreview, styles.weekChartPreview, style]}>
        {visibleMetrics.map((metric, index) => (
          <View key={metric.key} style={[styles.weekMetricRow, index > 0 && styles.weekMetricRowSeparated]}>
            {index > 0 ? <View pointerEvents="none" style={styles.weekMetricSeparator} /> : null}
            <MetricPlot axisLabels={axisLabels} days={days} fullWidth metric={metric} values={metricValues?.[metric.key]} />
          </View>
        ))}
        {showAllocation ? <View style={[styles.weekMetricRow, visibleMetrics.length > 0 && styles.weekMetricRowSeparated]}>
          {visibleMetrics.length > 0 ? <View pointerEvents="none" style={styles.weekMetricSeparator} /> : null}
          <AllocationPlot axisLabels={axisLabels} days={days} fullWidth values={liveAllocationValues} />
        </View> : null}
      </View>
    );
  }

  return (
    <View accessibilityLabel="Gráficos de KPI del programa" style={[styles.chartPreview, styles.programChartPreview, style]}>
      <View style={[styles.metricColumn, metricColumnStyle]}>
        <View style={styles.axisLeadingCell}>
          <Text style={[styles.axisChip, styles.axisLeadingChip]}>{axisLeadingLabel ?? programWeekRangeLabel(axisLabels)}</Text>
        </View>
        {metricRows.map((metric) => (
          <MetricIdentity color={metric.color} key={metric.key} label={metric.label} metricKey={metric.key} range={liveRange(metric, metricValues?.[metric.key])} />
        ))}
        <View style={[styles.metricIdentity, styles.allocationIdentity]}>
          <Text style={styles.metricTitle}>Alloc</Text>
          <View style={styles.allocationRanges}>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.protein }]}>P {allocationRange(liveAllocationValues, 0, "27 - 32%")}</Text>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.carbs }]}>C {allocationRange(liveAllocationValues, 1, "43 - 49%")}</Text>
            <Text style={[styles.allocationRange, { backgroundColor: tokens.color.fat }]}>G {allocationRange(liveAllocationValues, 2, "22 - 26%")}</Text>
          </View>
        </View>
      </View>
      <View onLayout={({ nativeEvent }) => setPlotViewportWidth(nativeEvent.layout.width)} style={styles.chartViewport}>
        <ScrollView
          directionalLockEnabled
          horizontal
          nestedScrollEnabled
          showsHorizontalScrollIndicator={axisLabels.length > 8}
        >
          <View style={[styles.scrollableCharts, chartContentWidth ? { width: chartContentWidth } : styles.scrollableChartsPending]}>
            <ChartAxisLabels labels={axisLabels} />
            {metricRows.map((metric) => (
              <MetricPlot days={days} key={metric.key} metric={metric} values={metricValues?.[metric.key]} />
            ))}
            <AllocationPlot days={days} values={liveAllocationValues} />
          </View>
        </ScrollView>
      </View>
    </View>
  );
}

export function ProgramMetricPreview(props: MetricPreviewProps) {
  return <MetricPreview {...props} scope="program" />;
}

export function WeekMetricPreview(props: MetricPreviewProps & { filter?: WeekMetricFilter }) {
  return <MetricPreview {...props} scope="week" />;
}

export function ProgramChildCard({
  title,
  weeksCount,
  filledDaysCount,
  foodsCount,
  onOpen,
  headingLink,
  openActionLabel,
  onMore,
  metricData,
  axisLabels,
}: {
  title: string;
  weeksCount: number;
  filledDaysCount: number;
  foodsCount: number;
  onOpen?: () => void;
  headingLink?: EntityHeadingLink;
  openActionLabel?: string;
  onMore?: () => void;
  metricData?: ProgramMetricDatum[];
  axisLabels?: string[];
}) {
  const [metricsExpanded, setMetricsExpanded] = useState(true);
  return (
    <Card accent={tokens.color.program}>
      <EntityHeading
        entity="program"
        headingLink={headingLink}
        indicators={[
          { label: "semanas", value: `${weeksCount} SEMANAS` },
          { icon: "dailyPlan", label: "minutas asignadas", value: filledDaysCount },
          { icon: "food", label: "alimentos", value: foodsCount },
        ]}
        title={title}
      />

      <View style={[styles.footer, metricsExpanded ? styles.footerExpanded : styles.footerCollapsed]}>
        <EntityCardActions leading={<EntityCardPanelToggle activeColor={tokens.color.dailyPlan} expanded={metricsExpanded} icon="chart" label={`métricas de ${title}`} onPress={() => setMetricsExpanded((current) => !current)} text="Semanas" />}>
          {onMore ? <EntityCardAction label="Más acciones" onPress={onMore}>
            <MoreHorizontal color={tokens.color.textMuted} size={19} strokeWidth={2.2} />
          </EntityCardAction> : null}
          {onOpen ? openActionLabel
            ? <Pressable accessibilityLabel={openActionLabel} accessibilityRole="button" onPress={onOpen} style={({ pressed }) => [styles.actionButtonLabeled, pressed && styles.pressed]}><Text style={styles.actionButtonLabel}>{openActionLabel}</Text></Pressable>
            : <EntityCardAction label="Ver programa" onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} /></EntityCardAction>
          : null}
        </EntityCardActions>
      </View>

      {metricsExpanded ? <ProgramMetricPreview axisLabels={axisLabels} data={metricData} days={metricData?.length ?? 14} style={layoutStyles.cardContentBleed} /> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.62 },
  chartPreview: { alignItems: "stretch" },
  programChartPreview: { flexDirection: "row", marginTop: tokens.spacing.sm },
  weekChartPreview: { gap: tokens.spacing.lg, marginTop: tokens.spacing.sm },
  weekMetricRow: { gap: tokens.spacing.xs, width: "100%" },
  weekMetricRowSeparated: { paddingTop: tokens.spacing.lg },
  weekMetricSeparator: { backgroundColor: tokens.color.borderSoft, height: 1, left: -tokens.layout.reducedInset, position: "absolute", right: -tokens.layout.reducedInset, top: 0 },
  metricColumn: { flexGrow: 0, flexShrink: 0, gap: tokens.spacing.compact },
  axisLeadingCell: { alignItems: "stretch", justifyContent: "center", minHeight: 22 },
  axisChip: { backgroundColor: "transparent", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, minHeight: 22, paddingTop: tokens.spacing.xs, textAlign: "center" },
  axisLeadingChip: { paddingHorizontal: tokens.spacing.sm, textAlign: "left", width: "100%" },
  chartViewport: { flex: 1, minWidth: 0 },
  scrollableCharts: { gap: tokens.spacing.compact },
  scrollableChartsPending: { minWidth: "100%" },
  weekLabels: { flexDirection: "row", minHeight: 22, width: "100%" },
  weekLabelCell: { flex: 1, minWidth: 0, paddingHorizontal: 1 },
  weekLabel: { width: "100%" },
  metricRow: { alignItems: "stretch", flexDirection: "row", minWidth: 0 },
  metricIdentity: { alignContent: "center", backgroundColor: tokens.color.surfaceMuted, borderBottomLeftRadius: tokens.radius.md, borderTopLeftRadius: tokens.radius.md, flexGrow: 0, flexShrink: 0, gap: tokens.spacing.xs, height: 58, justifyContent: "center", paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.compact },
  metricTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold, lineHeight: 20 },
  rangeBadge: { alignSelf: "flex-start", borderRadius: tokens.radius.sm, color: tokens.color.textMain, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold, maxWidth: "100%", overflow: "hidden", paddingHorizontal: tokens.spacing.compact, paddingVertical: 2 },
  rangeBadgeCalories: { backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderWidth: 1 },
  rangeBadgeDarkText: { color: tokens.color.surfaceApp },
  metricPlot: { backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.surfaceMuted, borderTopRightRadius: tokens.radius.md, borderBottomRightRadius: tokens.radius.md, borderWidth: 1, height: 58, minWidth: 0, overflow: "hidden", paddingVertical: tokens.spacing.compact, width: "100%" },
  weekFullWidthPlot: { backgroundColor: "transparent", borderRadius: tokens.radius.md, borderWidth: 0, height: 116 },
  weekMetricPlot: { height: 116, paddingVertical: 0 },
  pointLabels: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  pointLabel: { color: tokens.color.textMain, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.medium, marginLeft: -25, position: "absolute", textAlign: "center", transform: [{ translateY: -2 }], width: 50 },
  inlineDayLabels: { alignItems: "flex-end", bottom: 3, flexDirection: "row", left: 0, position: "absolute", right: 0 },
  inlineDayLabel: { color: tokens.color.textMuted, flex: 1, fontSize: 10, fontWeight: tokens.weight.medium, textAlign: "center" },
  inlineChartTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold, left: tokens.spacing.xs, lineHeight: 20, position: "absolute", top: tokens.spacing.xs, zIndex: 1 },
  inlineChartUnit: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.medium, lineHeight: 18, minWidth: 34, paddingHorizontal: tokens.spacing.sm, position: "absolute", right: tokens.spacing.xs, textAlign: "center", top: tokens.spacing.xs, zIndex: 1 },
  allocationIdentity: { height: 94, paddingVertical: tokens.spacing.sm },
  allocationRanges: { alignItems: "flex-start", gap: 3 },
  allocationRange: { borderRadius: tokens.radius.sm, color: tokens.color.surfaceApp, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, overflow: "hidden", paddingHorizontal: tokens.spacing.compact, paddingVertical: 2 },
  allocationPlot: { alignItems: "stretch", flexDirection: "row", height: 94, paddingVertical: tokens.spacing.sm },
  weekAllocationPlot: { height: 198, paddingBottom: tokens.spacing.xl, paddingTop: 28 },
  allocationSlot: { flex: 1, flexDirection: "column-reverse", gap: 2, minWidth: 0, paddingHorizontal: 1 },
  allocationSegment: { alignItems: "center", borderRadius: 4, justifyContent: "center", minHeight: 1 },
  weekAllocationSegment: { borderRadius: 8, overflow: "hidden" },
  allocationSegmentLabel: { color: tokens.color.surfaceApp, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: "900", zIndex: 1 },
  weekDivider: { borderLeftColor: tokens.color.borderSoft, borderLeftWidth: 1 },
  footer: { marginTop: 2 },
  footerCollapsed: { marginBottom: -2 },
  footerExpanded: { marginBottom: 2 },
  actionButtonLabeled: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.pill, justifyContent: "center", minHeight: 38, minWidth: 112, paddingHorizontal: tokens.spacing.lg },
  actionButtonLabel: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: "800" },
});
