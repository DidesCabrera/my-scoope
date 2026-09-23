import { useState } from "react";
import { Text, View } from "react-native";

import type { ProposalProgram } from "@/api/types";
import { Button, Card, InlineNotice, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { ProposalDailyPlanCard, ProposalMealCard } from "./proposal-preview";

export function ProposalProgramPreview({ program, onOpenFood }: { program: ProposalProgram; onOpenFood?(id: number): void }) {
  const [week, setWeek] = useState(1);
  const [dayNumber, setDayNumber] = useState(1);
  const day = program.days.find((item) => item.week_number === week && item.day_number === dayNumber);
  return (
    <View style={{ gap: tokens.spacing.md }}>
      <Card>
        <Text style={textStyles.strong}>{program.name}</Text>
        <Text style={textStyles.muted}>{program.duration_weeks} semanas · {program.days.length} días. Revisa cantidades y repeticiones. Aplicar guarda el programa; no lo calendariza.</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm }}>
          {Array.from({ length: program.duration_weeks }, (_, index) => index + 1).map((number) => (
            <Button key={number} label={`Semana ${number}`} onPress={() => setWeek(number)} variant={week === number ? "primary" : "secondary"} />
          ))}
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm }}>
          {Array.from({ length: 7 }, (_, index) => index + 1).map((number) => (
            <Button key={number} label={`Día ${number}`} onPress={() => setDayNumber(number)} variant={dayNumber === number ? "primary" : "secondary"} />
          ))}
        </View>
      </Card>
      {program.warnings?.map((warning) => <InlineNotice key={warning} tone="warning">{warning}</InlineNotice>)}
      {day ? <>
        <ProposalDailyPlanCard dailyplan={day.dailyplan} />
        {day.dailyplan.meals.map((item, index) => (
          <ProposalMealCard key={index} eyebrow={`Comida ${index + 1}`} meal={item.meal} onOpenFood={onOpenFood} time={item.hour} />
        ))}
      </> : null}
    </View>
  );
}
