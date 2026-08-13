import { type Href, useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ComparisonKind, ComparisonMetric, ComparisonResult } from "@/api/types";
import { Card, InlineNotice, SectionTitle } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function libraryHref(kind: ComparisonKind, id: number): Href {
  const segment = kind === "dailyplans" ? "daily-plans" : kind;
  return `/libraries/${segment}/${id}` as Href;
}

function metricColor(metric: ComparisonMetric): string {
  if (metric.key === "total_kcal") return tokens.color.kcalBorder;
  if (metric.key === "ppk") return tokens.color.ppk;
  if (metric.key.includes("protein")) return tokens.color.protein;
  if (metric.key.includes("carbs")) return tokens.color.carbs;
  return tokens.color.fat;
}

export function ComparisonResultCards({ result }: { result: ComparisonResult }) {
  const router = useRouter();
  return (
    <View style={styles.container}>
      <SectionTitle detail={`${result.items.length} slots`} title="Resultados comparativos" />
      {result.historical_snapshot ? (
        <InlineNotice>
          Esta es la fotografía guardada. Sus cifras no cambian cuando editas las entidades de origen.
        </InlineNotice>
      ) : null}
      {result.metrics.map((metric) => {
        const color = metricColor(metric);
        return (
          <Card key={metric.key}>
            <View style={styles.metricHeading}>
              <Text style={styles.metricTitle}>{metric.label}</Text>
              <Text style={styles.metricUnit}>{metric.unit}</Text>
            </View>
            <View style={styles.bars}>
              {metric.bars.map((bar) => (
                <Pressable
                  accessibilityHint="Abre la entidad en tu librería"
                  accessibilityLabel={`${bar.label}, ${bar.formatted_value}`}
                  accessibilityRole="button"
                  key={`${bar.position}-${bar.id}`}
                  onPress={() => router.push(libraryHref(result.kind, bar.id))}
                  style={({ pressed }) => [styles.barRow, pressed && styles.pressed]}>
                  <View style={styles.barMeta}>
                    <View style={[styles.positionBadge, { backgroundColor: color }]}>
                      <Text style={styles.positionText}>{bar.position}</Text>
                    </View>
                    <Text numberOfLines={2} style={styles.barLabel}>
                      {bar.label}{bar.quantity != null ? <Text style={styles.quantity}> ({Math.round(bar.quantity)}g)</Text> : null}
                    </Text>
                    <Text style={styles.barValue}>{bar.formatted_value}</Text>
                  </View>
                  <View style={styles.track}>
                    <View style={[styles.fill, { backgroundColor: color, width: `${Math.max(0, Math.min(bar.relative_percentage, 100))}%` }]} />
                  </View>
                </Pressable>
              ))}
            </View>
          </Card>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  barLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: "700" },
  barMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  barRow: { gap: tokens.spacing.xs },
  barValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: "700" },
  bars: { gap: tokens.spacing.md },
  container: { gap: tokens.spacing.md },
  fill: { borderRadius: 5, height: "100%" },
  metricHeading: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  metricTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  metricUnit: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: "700" },
  positionBadge: { alignItems: "center", borderRadius: 5, height: 22, justifyContent: "center", width: 22 },
  positionText: { color: "#111111", fontSize: 12, fontWeight: "900" },
  pressed: { opacity: 0.7 },
  quantity: { color: tokens.color.textSoft, fontWeight: "500" },
  track: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: 5, height: 22, overflow: "hidden" },
});
