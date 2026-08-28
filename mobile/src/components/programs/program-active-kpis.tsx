import { CalendarDays, CheckCheck, Clock3 } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { adheredDays: number; adherence: number; bleed?: boolean; elapsedDays: number; endDate: string; plannedAdherenceDays: number; progress: number; standalone?: boolean; startDate: string; totalDays: number };

export function ProgramActiveKpis({ adheredDays, adherence, bleed = true, elapsedDays, endDate, plannedAdherenceDays, progress, standalone = false, startDate, totalDays }: Props) {
  const advancement = Math.max(0, Math.min(progress, 100));
  const compliance = Math.max(0, Math.min(adherence, 100));
  const content = <>
    <View style={styles.periodRow}><View style={styles.periodIdentity}><CalendarDays color={tokens.color.textMuted} size={20} /><Text style={styles.metricLabel}>Periodo</Text></View><Text style={styles.periodDates}>{startDate}  —  {endDate}</Text></View>
    <View style={[styles.indicators, styles.indicatorsSurfaceReset]}>
      <View style={[styles.indicator, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><Clock3 color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Días recorridos</Text></View>
        <View style={styles.indicatorValue}><Text style={styles.fraction}>{elapsedDays}/{totalDays}</Text><Text style={styles.percentageText}>{advancement}%</Text></View>
        <View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: advancement }} style={styles.track}><View style={[styles.fill, { backgroundColor: tokens.color.dailyPlan, width: `${advancement}%` }]} /></View>
      </View>
      <View style={[styles.indicator, styles.indicatorMetricSpacing]}>
        <View style={styles.indicatorIdentity}><CheckCheck color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Adhesión</Text></View>
        <View style={styles.indicatorValue}><Text style={styles.fraction}>{adheredDays}/{plannedAdherenceDays}</Text><Text style={styles.percentageText}>{compliance}%</Text></View>
        <View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: compliance }} style={styles.track}><View style={[styles.fill, { backgroundColor: tokens.color.meal, width: `${compliance}%` }]} /></View>
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
  card:{gap:tokens.spacing.md},standalone:{alignSelf:"stretch",gap:tokens.spacing.md,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},header:{alignItems:"flex-start",flexDirection:"row",gap:tokens.spacing.md,justifyContent:"space-between"},headerCopy:{flex:1,gap:2},eyebrow:{color:tokens.color.program,fontSize:10,fontWeight:tokens.weight.bold,letterSpacing:1},title:{color:tokens.color.textMain,fontSize:tokens.type.body,fontWeight:tokens.weight.bold},periodRow:{alignItems:"center",backgroundColor:tokens.color.surfaceCard,borderColor:tokens.color.borderSoft,borderRadius:tokens.radius.md,borderWidth:1,flexDirection:"row",gap:tokens.spacing.sm,justifyContent:"space-between",marginTop:tokens.spacing.sm,padding:tokens.spacing.md},periodIdentity:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs},metricLabel:{color:tokens.color.textSoft,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold},metricValue:{color:tokens.color.textMain,fontSize:tokens.type.caption,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},periodDates:{color:tokens.color.textMain,fontSize:tokens.type.body,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},
  indicators:{backgroundColor:tokens.color.surfaceMuted,borderRadius:tokens.radius.lg,flexDirection:"row",gap:tokens.spacing.sm,padding:tokens.spacing.sm},indicator:{backgroundColor:tokens.color.surfaceCard,borderColor:tokens.color.borderSoft,borderRadius:tokens.radius.md,borderWidth:1,flex:1,gap:tokens.spacing.xs,minWidth:0,padding:tokens.spacing.md},indicatorIdentity:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs,minWidth:0},indicatorLabel:{color:tokens.color.textMain,flexShrink:1,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold},indicatorValue:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs,justifyContent:"space-between",marginTop:tokens.spacing.sm},fraction:{color:tokens.color.textMain,fontSize:tokens.type.section,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},percentageText:{color:tokens.color.textMain,fontSize:tokens.type.section,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},track:{backgroundColor:tokens.color.borderDefault,borderRadius:tokens.radius.pill,height:10,overflow:"hidden"},fill:{borderRadius:tokens.radius.pill,height:"100%"},
});
