import type { PropsWithChildren } from "react";
import { View } from "react-native";

import type { LibraryEntity, LibraryIndicator, LibraryNutrition } from "@/api/types";
import { NutritionKpiSection } from "@/components/nutrition/nutrition-kpi-section";

import { EntityCard, EntityCardPanelSlot } from "./entity-card";

export function NutritionEntityCard({ children, entity, indicators, nutrition, subtitle, title }: PropsWithChildren<{
  entity: LibraryEntity;
  indicators?: LibraryIndicator[];
  nutrition: LibraryNutrition;
  subtitle?: string;
  title: string;
}>) {
  return (
    <EntityCard entity={entity} indicators={indicators} subtitle={subtitle} title={title}>
      <View>
        <NutritionKpiSection
          calories={nutrition.calories}
          carbs={nutrition.carbs}
          density="regular"
          fat={nutrition.fat}
          protein={{ ...nutrition.protein, perKilogram: nutrition.protein.per_kilogram }}
        />
      </View>
      {children ? <EntityCardPanelSlot>{children}</EntityCardPanelSlot> : null}
    </EntityCard>
  );
}
