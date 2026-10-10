import { CheckCheck, Clock3 } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { adheredDays: number; adherence: number; bleed?: boolean; elapsedDays: number; mutedPanels?: boolean; plannedAdherenceDays: number; progress: number; standalone?: boolean; topInset?: boolean; totalDays: number };

const RING_SIZE = 136;
const RING_CENTER = RING_SIZE / 2;
const RING_RADIUS = 59;
const RING_STROKE_WIDTH = 8;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

function ProgressRing({ color, current, percentage, total, trackColor }: { color: string; current: number; percentage: number; total: number; trackColor: string }) {
  const dashOffset = RING_CIRCUMFERENCE * (1 - percentage / 100);
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: percentage }}
      style={styles.progressRing}>
      <Svg aria-hidden height={RING_SIZE} pointerEvents="none" style={StyleSheet.absoluteFill} viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`} width={RING_SIZE}>
        <Circle cx={RING_CENTER} cy={RING_CENTER} fill="none" r={RING_RADIUS} stroke={trackColor} strokeWidth={RING_STROKE_WIDTH} />
        <Circle
          cx={RING_CENTER}
          cy={RING_CENTER}
          fill="none"
          r={RING_RADIUS}
          stroke={color}
          strokeDasharray={`${RING_CIRCUMFERENCE} ${RING_CIRCUMFERENCE}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          strokeWidth={RING_STROKE_WIDTH}
          transform={`rotate(-90 ${RING_CENTER} ${RING_CENTER})`}
        />
      </Svg>
      <View style={styles.ringValue}>
        <Text style={styles.fraction}>{current}/{total}</Text>
        <Text style={styles.percentageText}>{percentage}%</Text>
      </View>
    </View>
  );
}

export function ProgramActiveKpis({ adheredDays, adherence, bleed = true, elapsedDays, mutedPanels = false, plannedAdherenceDays, progress, standalone = false, topInset = false, totalDays }: Props) {
  const advancement = Math.max(0, Math.min(progress, 100));
  const compliance = Math.max(0, Math.min(adherence, 100));
  const content = <>
    <View style={[styles.indicators, styles.indicatorsSurfaceReset]}>
      <View style={[styles.indicator, mutedPanels ? styles.indicatorMuted : styles.indicatorCard, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><Clock3 color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Planes diarios recorridos</Text></View>
        <ProgressRing color={tokens.color.dailyPlan} current={elapsedDays} percentage={advancement} total={totalDays} trackColor={`${tokens.color.dailyPlan}33`} />
      </View>
      <View style={[styles.indicator, mutedPanels ? styles.indicatorMuted : styles.indicatorCard, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><CheckCheck color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Cumplimiento comidas</Text></View>
        <ProgressRing color={tokens.color.meal} current={adheredDays} percentage={compliance} total={plannedAdherenceDays} trackColor={`${tokens.color.meal}33`} />
      </View>
    </View>
  </>;
  return standalone ? <View style={[styles.standalone, bleed ? styles.standaloneBleed : styles.standaloneInset, topInset ? styles.standaloneTopInset : undefined]}>{content}</View> : <Card accent={tokens.color.program} style={styles.card}>{content}</Card>;
}

const styles = StyleSheet.create({
  indicatorsSurfaceReset:{backgroundColor:"transparent",borderRadius:0,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding,padding:tokens.spacing.xs},
  indicatorMetricSpacing:{gap:tokens.spacing.sm},
  standaloneBleed:{marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},
  standaloneInset:{marginHorizontal:0},
  standaloneTopInset:{marginTop:tokens.spacing.sm},
  card:{gap:tokens.spacing.md},standalone:{alignSelf:"stretch",gap:tokens.spacing.md,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},header:{alignItems:"flex-start",flexDirection:"row",gap:tokens.spacing.md,justifyContent:"space-between"},headerCopy:{flex:1,gap:2},eyebrow:{color:tokens.color.program,fontSize:10,fontWeight:tokens.component.eyebrow.fontWeight,letterSpacing:1},title:{color:tokens.color.textMain,fontSize:tokens.type.body,fontWeight:tokens.weight.bold},
  indicators:{alignSelf:"stretch",backgroundColor:tokens.color.surfaceMuted,borderRadius:tokens.radius.lg,flexDirection:"row",gap:tokens.spacing.sm,padding:tokens.spacing.sm},indicator:{alignItems:"center",borderRadius:tokens.radius.panel,flexBasis:0,flexGrow:1,flexShrink:1,gap:tokens.spacing.xs,minWidth:0,paddingHorizontal:tokens.spacing.md,paddingVertical:tokens.spacing.lg},indicatorCard:{backgroundColor:tokens.color.surfaceCard},indicatorMuted:{backgroundColor:tokens.color.surfaceMuted},indicatorIdentity:{alignItems:"center",alignSelf:"stretch",flexDirection:"column",gap:tokens.spacing.xs,justifyContent:"center",minWidth:0},indicatorLabel:{color:tokens.color.textMain,flexShrink:1,fontSize:18,fontWeight:tokens.weight.semibold,textAlign:"center"},progressRing:{alignItems:"center",height:RING_SIZE,justifyContent:"center",width:RING_SIZE},ringValue:{alignItems:"center",justifyContent:"center"},fraction:{color:tokens.color.textMain,fontSize:tokens.type.title,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},percentageText:{color:tokens.color.textMuted,fontSize:tokens.type.body,fontWeight:tokens.weight.semibold,fontVariant:["tabular-nums"],marginTop:2},
});
