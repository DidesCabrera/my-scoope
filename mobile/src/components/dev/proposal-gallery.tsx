import type { ProposalSummary } from "@/api/types";
import { MealPanels, type MealPanelItem } from "@/components/panels";
import {
  ProposalCard,
  ProposalDetailPage,
  ProposalEntitySection,
  ProposalListCard,
  ProposalObjectiveSection,
  ProposalReviewActions,
} from "@/components/proposals";
import { NutritionEntityCard } from "@/components/nutrition";
import { SectionTitle } from "@/components/ui";

const meals: MealPanelItem[] = [
  { id: "breakfast", name: "Desayuno", time: "08:00", foods: [{ name: "Avena", quantity: 80, quantityUnit: "g" }], calories: 594, calorieShare: 28, proteinGrams: 29.8, carbsGrams: 88.4, fatGrams: 13, proteinAllocation: 20, carbsAllocation: 60, fatAllocation: 20 },
  { id: "lunch", name: "Almuerzo", time: "13:30", foods: [{ name: "Pollo", quantity: 160, quantityUnit: "g" }], calories: 720, calorieShare: 34, proteinGrams: 52, carbsGrams: 82, fatGrams: 20, proteinAllocation: 29, carbsAllocation: 46, fatAllocation: 25 },
  { id: "dinner", name: "Cena", time: "20:00", foods: [{ name: "Salmón", quantity: 170, quantityUnit: "g" }], calories: 610, calorieShare: 29, proteinGrams: 43, carbsGrams: 58, fatGrams: 23, proteinAllocation: 28, carbsAllocation: 38, fatAllocation: 34 },
];

const proposalSummaryExample: ProposalSummary = {
  actions: [],
  attachment_kind: "dailyplan",
  attachment_label: "Plan diario propuesto",
  attachment_name: "Día de entrenamiento",
  created_at: "2026-10-07T14:30:00-03:00",
  id: 101,
  is_reviewable: true,
  source: "ai",
  status: "pending_review",
  status_label: "Pendiente de revisión",
  summary: "Crear un plan diario alto en proteína para un día de entrenamiento.",
  title: "Propuesta de plan diario",
};

export function ProposalGallery() {
  return (
    <>
      <SectionTitle detail="Componente compartido por el tab Propuestas y el chat" title="Card de propuesta del Asistente" />
      <ProposalListCard onPress={() => undefined} proposal={proposalSummaryExample} />
      <SectionTitle detail="Resumen de bandeja" title="Card de propuesta" />
      <ProposalCard attachment={{ kind: "dailyPlan", name: "Día de entrenamiento propuesto" }} isRead={false} onPress={() => undefined} receivedAt="Recibida hoy, 14:30" status="pending" summary="Crear un DailyPlan alto en proteína para un día de entrenamiento." title="Propuesta de DailyPlan" />
      <SectionTitle detail="Revisión antes de aplicar" title="Detalle de propuesta" />
      <ProposalDetailPage
        isRead
        objectives={<ProposalObjectiveSection calories={2140} carbs={{ grams: 238, allocation: 44 }} fat={{ grams: 62, allocation: 26 }} protein={{ grams: 155, allocation: 30, perKilogram: 1.8 }} />}
        receivedAt="Recibida hoy, 14:30"
        status="pending"
        summary="Crear un DailyPlan alto en proteína para un día de entrenamiento."
        title="Propuesta de DailyPlan"
        typeKind="dailyPlan"
        proposedEntity={
          <ProposalEntitySection entity="dailyPlan">
            <NutritionEntityCard entity="dailyPlan" indicators={[{ icon: "meal", label: "comidas", value: 3 }, { icon: "food", label: "alimentos", value: 9 }]} nutrition={{ calories: 2140, carbs: { grams: 238, allocation: 44 }, fat: { grams: 62, allocation: 26 }, protein: { grams: 155, allocation: 30, perKilogram: 1.8 } }} title="Día de entrenamiento propuesto">
              <MealPanels items={meals} />
            </NutritionEntityCard>
          </ProposalEntitySection>
        }>
        <ProposalReviewActions description="Aprobar confirma la revisión; aplicar cambios reales será un paso posterior y explícito." onApprove={() => undefined} onCancel={() => undefined} onReject={() => undefined} />
      </ProposalDetailPage>
    </>
  );
}
