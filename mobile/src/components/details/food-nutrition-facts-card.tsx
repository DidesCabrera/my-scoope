import type { FoodNutritionFacts } from "@/api/food-nutrition";
import { Card, CardHeader, KeyValueTable } from "@/components/ui";

import { foodNutritionFactRows } from "./food-nutrition-facts";

export function FoodNutritionFactsCard({
  nutrition,
  quantityUnit,
}: {
  nutrition: FoodNutritionFacts;
  quantityUnit: "g" | "ml";
}) {
  return (
    <Card>
      <CardHeader density="compact" title={`Información nutricional por 100 ${quantityUnit}`} />
      <KeyValueTable items={foodNutritionFactRows(nutrition)} />
    </Card>
  );
}
