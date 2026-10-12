import { NutritionFactsCard } from "@/components/ui";

export function NutritionFactsGallery() {
  return <>
    <NutritionFactsCard
      facts={{ proteinG: 9, totalFatG: 5, saturatedFatG: 3.2, carbsG: 3.9, sugarG: 3.6, fiberG: 0, sodiumMg: 36 }}
      portion={{ quantity: 150, unit: "g" }}
    />
  </>;
}
