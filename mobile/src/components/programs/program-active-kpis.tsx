import { CheckCheck, Clock3 } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { adheredDays: number; adherence: number; bleed?: boolean; elapsedDays: number; plannedAdherenceDays: number; progress: number; standalone?: boolean; totalDays: number };

const RING_SIZE = 112;
const RING_CENTER = RING_SIZE / 2;
const RING_RADIUS = 48;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

function ProgressRing({ color, current, percentage, total }: { color: string; current: number; percentage: number; total: number }) {
  const dashOffset = RING_CIRCUMFERENCE * (1 - percentage / 100);
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: percentage }}
      style={styles.progressRing}>
      <Svg aria-hidden height={RING_SIZE} pointerEvents="none" style={StyleSheet.absoluteFill} viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`} width={RING_SIZE}>
        <Circle cx={RING_CENTER} cy={RING_CENTER} fill="none" r={RING_RADIUS} stroke={tokens.color.borderDefault} strokeWidth={7} />
        <Circle
          cx={RING_CENTER}
          cy={RING_CENTER}
          fill="none"
          r={RING_RADIUS}
          stroke={color}
          strokeDasharray={`${RING_CIRCUMFERENCE} ${RING_CIRCUMFERENCE}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          strokeWidth={7}
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

export function ProgramActiveKpis({ adheredDays, adherence, bleed = true, elapsedDays, plannedAdherenceDays, progress, standalone = false, totalDays }: Props) {
  const advancement = Math.max(0, Math.min(progress, 100));
  const compliance = Math.max(0, Math.min(adherence, 100));
  const content = <>
    <View style={[styles.indicators, styles.indicatorsSurfaceReset]}>
      <View style={[styles.indicator, styles.indicatorElapsed, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><Clock3 color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Días recorridos</Text></View>
        <ProgressRing color={tokens.color.dailyPlan} current={elapsedDays} percentage={advancement} total={totalDays} />
      </View>
      <View style={[styles.indicator, styles.indicatorAdherence, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><CheckCheck color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Adhesión</Text></View>
        <ProgressRing color={tokens.color.meal} current={adheredDays} percentage={compliance} total={plannedAdherenceDays} />
      </View>
    </View>
  </>;
  return standalone ? <View style={[styles.standalone, bleed ? styles.standaloneBleed : styles.standaloneInset]}>{content}</View> : <Card accent={tokens.color.program} style={styles.card}>{content}</Card>;
}

const styles = StyleSheet.create({
  indicatorsSurfaceReset:{backgroundColor:"transparent",borderRadius:0,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding,padding:tokens.spacing.xs},
  indicatorMetricSpacing:{gap:tokens.spacing.sm},
  standaloneBleed:{marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},
  standaloneInset:{marginHorizontal:0},
  card:{gap:tokens.spacing.md},standalone:{alignSelf:"stretch",gap:tokens.spacing.md,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},header:{alignItems:"flex-start",flexDirection:"row",gap:tokens.spacing.md,justifyContent:"space-between"},headerCopy:{flex:1,gap:2},eyebrow:{color:tokens.color.program,fontSize:10,fontWeight:tokens.component.eyebrow.fontWeight,letterSpacing:1},title:{color:tokens.color.textMain,fontSize:tokens.type.body,fontWeight:tokens.weight.bold},
  indicators:{alignSelf:"stretch",backgroundColor:tokens.color.surfaceMuted,borderRadius:tokens.radius.lg,flexDirection:"row",gap:tokens.spacing.sm,padding:tokens.spacing.sm},indicator:{alignItems:"center",backgroundColor:tokens.color.surfaceCard,borderColor:tokens.color.borderSoft,borderRadius:tokens.radius.md,borderWidth:1,flexBasis:0,flexGrow:1,flexShrink:1,gap:tokens.spacing.xs,minWidth:0,padding:tokens.spacing.md},indicatorIdentity:{alignItems:"center",alignSelf:"stretch",flexDirection:"row",gap:tokens.spacing.xs,minWidth:0},indicatorLabel:{color:tokens.color.textMain,flexShrink:1,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold},progressRing:{alignItems:"center",height:RING_SIZE,justifyContent:"center",marginTop:tokens.spacing.sm,width:RING_SIZE},ringValue:{alignItems:"center",justifyContent:"center"},fraction:{color:tokens.color.textMain,fontSize:tokens.type.section,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},percentageText:{color:tokens.color.textMuted,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold,fontVariant:["tabular-nums"],marginTop:2},
  indicatorElapsed:{backgroundColor:`${tokens.color.dailyPlan}1A`,borderColor:`${tokens.color.dailyPlan}80`},indicatorAdherence:{backgroundColor:`${tokens.color.meal}1A`,borderColor:`${tokens.color.meal}80`},
});
