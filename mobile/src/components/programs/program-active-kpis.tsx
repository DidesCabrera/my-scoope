import { CalendarDays, CheckCheck, Clock3 } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

type Props = { adheredDays: number; adherence: number; bleed?: boolean; elapsedDays: number; endDate: string; plannedAdherenceDays: number; progress: number; standalone?: boolean; startDate: string; totalDays: number };

export function ProgramActiveKpis({ adheredDays, adherence, bleed = true, elapsedDays, endDate, plannedAdherenceDays, progress, standalone = false, startDate, totalDays }: Props) {
  const advancement = Math.max(0, Math.min(progress, 100));
  const compliance = Math.max(0, Math.min(adherence, 100));
  const content = <>
    <View style={[styles.periodRow, styles.periodBorder]}><View style={styles.periodIdentity}><CalendarDays color="#FFFFFF" size={20} /><Text style={[styles.metricLabel, styles.periodText]}>Periodo</Text></View><Text style={styles.periodDates}>{startDate}  —  {endDate}</Text></View>
    <View style={[styles.indicators, styles.indicatorsSurfaceReset]}>
      <View style={[styles.indicator, styles.indicatorMetricSpacing]}><View style={styles.indicatorRow}><View style={styles.indicatorIdentity}><Clock3 color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Días transcurridos</Text></View><View style={styles.indicatorValue}><Text style={styles.fraction}>{elapsedDays}/{totalDays}</Text><View style={[styles.percentageTag, { backgroundColor: tokens.color.dailyPlan }]}><Text style={styles.percentageText}>{advancement}%</Text></View></View></View><View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: advancement }} style={styles.track}><View style={[styles.fill, { backgroundColor: tokens.color.dailyPlan, width: `${advancement}%` }]} /></View></View>
      <View style={styles.indicatorDivider} />
      <View style={[styles.indicator, styles.indicatorMetricSpacing]}><View style={styles.indicatorRow}><View style={styles.indicatorIdentity}><CheckCheck color={tokens.color.textMuted} size={20} /><Text style={styles.indicatorLabel}>Adhesión</Text></View><View style={styles.indicatorValue}><Text style={styles.fraction}>{adheredDays}/{plannedAdherenceDays}</Text><View style={[styles.percentageTag, { backgroundColor: tokens.color.meal }]}><Text style={styles.percentageText}>{compliance}%</Text></View></View></View><View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: compliance }} style={styles.track}><View style={[styles.fill, { backgroundColor: tokens.color.meal, width: `${compliance}%` }]} /></View></View>
    </View>
  </>;
  return standalone ? <View style={[styles.standalone, bleed ? styles.standaloneBleed : styles.standaloneInset]}>{content}</View> : <Card accent={tokens.color.program} style={styles.card}>{content}</Card>;
}

const styles = StyleSheet.create({
  periodBorder:{borderWidth:3},
  indicatorsSurfaceReset:{backgroundColor:"transparent",borderRadius:0,padding:tokens.spacing.xs},
  indicatorMetricSpacing:{gap:tokens.spacing.sm},
  standaloneBleed:{marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},
  standaloneInset:{marginHorizontal:0},
  card:{gap:tokens.spacing.md},standalone:{alignSelf:"stretch",gap:tokens.spacing.md,marginHorizontal:tokens.layout.reducedInset-tokens.card.outerPadding},header:{alignItems:"flex-start",flexDirection:"row",gap:tokens.spacing.md,justifyContent:"space-between"},headerCopy:{flex:1,gap:2},eyebrow:{color:tokens.color.program,fontSize:10,fontWeight:tokens.weight.bold,letterSpacing:1},title:{color:tokens.color.textMain,fontSize:tokens.type.body,fontWeight:tokens.weight.bold},periodRow:{alignItems:"center",backgroundColor:tokens.color.kcalSurface,borderColor:tokens.color.kcalBorder,borderRadius:tokens.radius.lg,borderWidth:2,flexDirection:"row",gap:tokens.spacing.sm,justifyContent:"space-between",marginTop:tokens.spacing.sm,padding:tokens.spacing.md},periodIdentity:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs},metricLabel:{color:tokens.color.textSoft,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold},metricValue:{color:tokens.color.textMain,fontSize:tokens.type.caption,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},periodText:{color:"#FFFFFF"},periodDates:{color:"#FFFFFF",fontSize:tokens.type.body,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},
  indicators:{backgroundColor:tokens.color.surfaceMuted,borderRadius:tokens.radius.lg,gap:tokens.spacing.sm,padding:tokens.spacing.sm},indicator:{gap:tokens.spacing.xs},indicatorRow:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.sm,justifyContent:"space-between"},indicatorIdentity:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs},indicatorLabel:{color:tokens.color.textMain,fontSize:tokens.type.caption,fontWeight:tokens.weight.semibold},indicatorValue:{alignItems:"center",flexDirection:"row",gap:tokens.spacing.xs},fraction:{color:tokens.color.textMain,fontSize:tokens.type.caption,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},percentageTag:{borderRadius:tokens.component.nutritionKpi.regular.barRadius,height:tokens.component.nutritionKpi.regular.barHeight,justifyContent:"center",paddingHorizontal:tokens.spacing.xs},percentageText:{color:"#FFFFFF",fontSize:tokens.type.caption,fontWeight:tokens.weight.bold,fontVariant:["tabular-nums"]},indicatorDivider:{backgroundColor:tokens.color.borderSoft,height:1},track:{backgroundColor:tokens.color.borderDefault,borderRadius:tokens.radius.pill,height:10,overflow:"hidden"},fill:{borderRadius:tokens.radius.pill,height:"100%"},
});
