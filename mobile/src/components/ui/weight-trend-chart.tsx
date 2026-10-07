import { useMemo, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Line, Path, Stop } from "react-native-svg";

import type { WeightItem } from "@/api/types";
import { tokens } from "@/design/tokens";

import { sortedWeightTrend } from "./weight-trend-values";

const CHART_HEIGHT = 176;
const PLOT_TOP = 12;
const PLOT_BOTTOM = 142;
const PLOT_LEFT = 42;
const PLOT_RIGHT = 12;

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

function decimal(value: number): string {
  return value.toLocaleString("es-CL", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
}

export function WeightTrendChart({ items }: { items: WeightItem[] }) {
  const [width, setWidth] = useState(0);
  const trend = useMemo(() => sortedWeightTrend(items), [items]);

  if (!trend.length) {
    return <Text style={styles.empty}>La tendencia aparecerá cuando registres tu primera medición.</Text>;
  }

  const weights = trend.map((item) => item.weight_kg);
  const rawMinimum = Math.min(...weights);
  const rawMaximum = Math.max(...weights);
  const padding = Math.max((rawMaximum - rawMinimum) * 0.18, 0.5);
  const minimum = rawMinimum - padding;
  const maximum = rawMaximum + padding;
  const availableWidth = Math.max(0, width - PLOT_LEFT - PLOT_RIGHT);
  const availableHeight = PLOT_BOTTOM - PLOT_TOP;
  const coordinates = trend.map((item, index) => ({
    x: trend.length === 1 ? PLOT_LEFT + availableWidth / 2 : PLOT_LEFT + (index / (trend.length - 1)) * availableWidth,
    y: PLOT_TOP + ((maximum - item.weight_kg) / (maximum - minimum)) * availableHeight,
  }));
  const linePath = coordinates.map(({ x, y }, index) => `${index ? "L" : "M"} ${x} ${y}`).join(" ");
  const areaPath = coordinates.length > 1
    ? `${linePath} L ${coordinates.at(-1)?.x} ${PLOT_BOTTOM} L ${coordinates[0].x} ${PLOT_BOTTOM} Z`
    : "";
  const guideValues = [maximum, (maximum + minimum) / 2, minimum];
  const first = trend[0];
  const last = trend.at(-1) ?? first;
  const accessibilityLabel = trend.length === 1
    ? `Tendencia de peso: ${decimal(first.weight_kg)} kilogramos el ${shortDate(first.measured_on)}`
    : `Tendencia de peso desde ${decimal(first.weight_kg)} kilogramos el ${shortDate(first.measured_on)} hasta ${decimal(last.weight_kg)} kilogramos el ${shortDate(last.measured_on)}`;

  return (
    <View
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="image"
      onLayout={({ nativeEvent }) => setWidth(nativeEvent.layout.width)}
      style={styles.container}>
      {width > 0 ? <>
        <Svg aria-hidden height={CHART_HEIGHT} pointerEvents="none" width={width}>
          <Defs>
            <LinearGradient id="weight-trend-area" x1="0" x2="0" y1="0" y2="1">
              <Stop offset="0" stopColor={tokens.color.protein} stopOpacity={0.3} />
              <Stop offset="1" stopColor={tokens.color.protein} stopOpacity={0} />
            </LinearGradient>
          </Defs>
          {guideValues.map((_, index) => {
            const y = PLOT_TOP + (index / (guideValues.length - 1)) * availableHeight;
            return <Line key={`guide-${index}`} stroke={tokens.color.borderDefault} strokeWidth={1} x1={PLOT_LEFT} x2={width - PLOT_RIGHT} y1={y} y2={y} />;
          })}
          {areaPath ? <Path d={areaPath} fill="url(#weight-trend-area)" /> : null}
          {coordinates.length > 1 ? <Path d={linePath} fill="none" stroke={tokens.color.protein} strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} /> : null}
          {coordinates.map(({ x, y }, index) => (
            <Circle key={trend[index].id} cx={x} cy={y} fill={tokens.color.surfaceMuted} r={4} stroke={tokens.color.protein} strokeWidth={2.5} />
          ))}
        </Svg>
        <View pointerEvents="none" style={styles.yLabels}>
          {guideValues.map((value, index) => <Text key={`weight-${index}`} style={styles.axisLabel}>{decimal(value)}</Text>)}
        </View>
        <View pointerEvents="none" style={styles.xLabels}>
          <Text style={styles.axisLabel}>{shortDate(first.measured_on)}</Text>
          {trend.length > 1 ? <Text style={[styles.axisLabel, styles.lastDate]}>{shortDate(last.measured_on)}</Text> : null}
        </View>
      </> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  axisLabel: { color: tokens.color.textSoft, fontSize: 11, fontVariant: ["tabular-nums"], lineHeight: 14 },
  container: { height: CHART_HEIGHT, minWidth: 0, position: "relative", width: "100%" },
  empty: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  lastDate: { textAlign: "right" },
  xLabels: { bottom: 0, flexDirection: "row", justifyContent: "space-between", left: PLOT_LEFT, position: "absolute", right: PLOT_RIGHT },
  yLabels: { bottom: CHART_HEIGHT - PLOT_BOTTOM - 7, justifyContent: "space-between", left: 0, position: "absolute", top: PLOT_TOP - 7, width: PLOT_LEFT - 7 },
});
