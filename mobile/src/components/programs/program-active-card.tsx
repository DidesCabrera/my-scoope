import { type Href, useRouter } from "expo-router";
import { CalendarClock } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { ActiveProgramData, CalendarizationData } from "@/api/types";
import { compactDateLabel } from "@/components/calendarization/current-week";
import { Card, DetailLinkRow, EntityHeading, HeaderMetadataChip } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { ProgramActiveKpis } from "./program-active-kpis";

type Props = { calendarization: CalendarizationData; program: ActiveProgramData };

export function ProgramActiveOverview({ calendarization, program, embedded = false }: Props & { embedded?: boolean }) {
  const router = useRouter();
  const activeIndicators = program.indicators.map((indicator) => indicator.icon === "week"
    ? { ...indicator, icon: undefined, value: `${indicator.value} ${Number(indicator.value) === 1 ? "SEMANA" : "SEMANAS"}` }
    : indicator);
  const content = (
    <>
      <EntityHeading entity="program" eyebrow="Programa activo" eyebrowAccessory={<HeaderMetadataChip kind="date" value={`${compactDateLabel(calendarization.start_date)} — ${compactDateLabel(calendarization.end_date)}`} />} identityIcon={CalendarClock} indicators={activeIndicators} title={calendarization.program_name} variant={embedded ? "card" : "page"} />
      <ProgramActiveKpis adheredDays={program.adherence?.completed_meals ?? 0} adherence={program.adherence?.adherence_percent ?? 0} elapsedDays={calendarization.progress_day} mutedPanels={embedded} plannedAdherenceDays={program.adherence?.elapsed_meals ?? program.adherence?.planned_meals ?? 0} progress={calendarization.progress_percent} standalone topInset={!embedded} totalDays={calendarization.progress_total_days} />
      {embedded ? <DetailLinkRow accessibilityLabel={`Ir a Mi programa activo: ${calendarization.program_name}`} label="Ir a Mi programa activo" onPress={() => router.push("/program" as Href)} /> : null}
    </>
  );
  return embedded
    ? <Card accent={tokens.color.program} style={styles.content}>{content}</Card>
    : <View style={styles.content}>{content}</View>;
}

export function ProgramActiveHomeOverview(props: Props) {
  return <ProgramActiveOverview {...props} embedded />;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.md },
});
