import { type Href, useRouter } from "expo-router";
import { Activity, CalendarClock } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { ActiveProgramData, CalendarizationData } from "@/api/types";
import { compactDateLabel } from "@/components/calendarization/current-week";
import { Card, DetailLinkRow, EntityHeading, SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { ProgramActiveKpis } from "./program-active-kpis";

type Props = { calendarization: CalendarizationData; program: ActiveProgramData };

export function ProgramActiveOverview({ calendarization, program, embedded = false }: Props & { embedded?: boolean }) {
  const router = useRouter();
  const content = (
    <>
      <EntityHeading entity="program" eyebrow="Programa activo" identityIcon={CalendarClock} indicators={[...(embedded ? [] : program.indicators), { icon: "week", iconPosition: "leading", label: "periodo", tone: "surfaceMuted", value: `${compactDateLabel(calendarization.start_date)} — ${compactDateLabel(calendarization.end_date)}` }]} title={calendarization.program_name} variant={embedded ? "card" : "page"} />
      {embedded ? null : <SectionHeading icon={<Activity color={tokens.color.entityIconForeground} size={18} />} title="Métricas de activación" />}
      <ProgramActiveKpis adheredDays={program.adherence?.completed_meals ?? 0} adherence={program.adherence?.adherence_percent ?? 0} bleed={false} elapsedDays={calendarization.progress_day} plannedAdherenceDays={program.adherence?.elapsed_meals ?? program.adherence?.planned_meals ?? 0} progress={calendarization.progress_percent} standalone totalDays={calendarization.progress_total_days} />
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
