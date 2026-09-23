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
  const specification = program.nutrition_specification;
  const target = specification?.weeks.find((item) => item.week === week);
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
      {target && specification ? <Card>
        <Text style={textStyles.strong}>Objetivos de la semana {week}</Text>
        <Text style={textStyles.body}>{Math.round(target.kcal)} kcal/día · Proteína {target.protein_min_g.toFixed(1)}–{target.protein_max_g.toFixed(1)} g/día</Text>
        <Text style={textStyles.body}>{specification.protein_min_ppk}–{specification.protein_max_ppk} g/kg · Grasa máxima {specification.fat_max_percent}% de las calorías reales de cada día</Text>
        <Text style={textStyles.muted}>Peso de referencia: {target.reference_weight_kg} kg ({specification.weight_basis === "projected" ? "proyección, no medición" : "peso medido"}). Una proyección no garantiza un cambio de peso.</Text>
      </Card> : null}
      {day ? <>
        <ProposalDailyPlanCard dailyplan={day.dailyplan} />
        {day.dailyplan.meals.map((item, index) => (
          <View key={index} style={{ gap: tokens.spacing.sm }}>
            <ProposalMealCard eyebrow={`Comida ${index + 1}`} meal={item.meal} onOpenFood={onOpenFood} time={item.hour} />
            {item.note ? <Text style={textStyles.muted}>{item.note}</Text> : null}
          </View>
        ))}
      </> : null}
    </View>
  );
}
