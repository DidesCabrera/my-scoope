import { type Href, useRouter } from "expo-router";
import { CalendarClock } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { ActiveProgramData, CalendarizationData } from "@/api/types";
import { Card, DetailLinkRow, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { ProgramActiveKpis } from "./program-active-kpis";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

type Props = { calendarization: CalendarizationData; program: ActiveProgramData };

export function ProgramActiveOverview({ calendarization, program, embedded = false }: Props & { embedded?: boolean }) {
  const router = useRouter();
  return (
    <View style={styles.content}>
      <EntityHeading entity="program" eyebrow="Programa en curso" identityIcon={CalendarClock} indicators={program.indicators} title={calendarization.program_name} variant={embedded ? "card" : "page"} />
      <ProgramActiveKpis adheredDays={program.adherence?.completed_meals ?? 0} adherence={program.adherence?.adherence_percent ?? 0} bleed={!embedded} elapsedDays={calendarization.progress_day} endDate={displayDate(calendarization.end_date)} plannedAdherenceDays={program.adherence?.elapsed_meals ?? program.adherence?.planned_meals ?? 0} progress={calendarization.progress_percent} standalone startDate={displayDate(calendarization.start_date)} totalDays={calendarization.progress_total_days} />
      {calendarization.source_program_id ? <DetailLinkRow accessibilityLabel={`Ir al detalle de ${calendarization.program_name}`} bleed={!embedded} label="Ir a detalle de programa" onPress={() => router.push(`/libraries/programs/${calendarization.source_program_id}` as Href)} /> : null}
    </View>
  );
}

export function ProgramActiveCard(props: Props) {
  return <Card accent={tokens.color.program} style={styles.card}><ProgramActiveOverview {...props} embedded /></Card>;
}

const styles = StyleSheet.create({
  card: { gap: tokens.spacing.md },
  content: { gap: tokens.spacing.md },
});
