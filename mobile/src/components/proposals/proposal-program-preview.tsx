import { useMemo } from "react";
import { View } from "react-native";

import type { ProposalFact, ProposalProgram } from "@/api/types";
import { ProgramDetailPreview } from "@/components/libraries/program-detail-preview";
import { InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { proposalProgramLibraryItem } from "./proposal-program-adapter";
import { ProposalFacts } from "./proposal-preview";

function decimal(value: number): string {
  return value.toLocaleString("es-CL", { maximumFractionDigits: 1 });
}

function weekRequirementFacts(program: ProposalProgram, week: number): ProposalFact[] {
  const specification = program.nutrition_specification;
  const target = specification?.weeks.find((item) => item.week === week);
  if (!specification || !target) return [];
  return [
    { label: "Energía diaria", value: `${Math.round(target.kcal).toLocaleString("es-CL")} kcal` },
    { label: "Proteína diaria", value: `${decimal(target.protein_min_g)}–${decimal(target.protein_max_g)} g` },
    { label: "Proteína por peso", value: `${decimal(specification.protein_min_ppk)}–${decimal(specification.protein_max_ppk)} g/kg` },
    { label: "Grasa máxima", value: `${decimal(specification.fat_max_percent)}% de las calorías` },
    { label: "Peso de referencia", value: `${decimal(target.reference_weight_kg)} kg · ${specification.weight_basis === "projected" ? "proyectado" : "medido"}` },
  ];
}

export function ProposalProgramPreview({ program, onOpenFood }: { program: ProposalProgram; onOpenFood?(id: number): void }) {
  const item = useMemo(() => proposalProgramLibraryItem(program), [program]);
  return (
    <ProgramDetailPreview
      footer={(
        <View style={{ gap: tokens.spacing.sm }}>
          {program.warnings?.map((warning) => <InlineNotice key={warning} tone="warning">{warning}</InlineNotice>)}
          <InlineNotice>Aplicar guarda este programa en tu biblioteca; no lo calendariza.</InlineNotice>
        </View>
      )}
      item={item}
      onOpenFood={onOpenFood}
      renderWeekContext={(week) => {
        const facts = weekRequirementFacts(program, week);
        return facts.length ? (
          <ProposalFacts
            description="Requisitos usados por el Asistente AI para validar los siete planes de esta semana."
            facts={facts}
            title={`Objetivos de la Semana ${week}`}
          />
        ) : null;
      }}
    />
  );
}
