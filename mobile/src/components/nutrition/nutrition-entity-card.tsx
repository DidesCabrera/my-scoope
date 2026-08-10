import type { ReactNode } from "react";
import { StyleProp, View, ViewStyle } from "react-native";

import {
  EntityCard,
  type EntityKind,
  type StructuralIndicator,
} from "@/components/ui";
import {
  NutritionKpiSection,
  type NutritionKpiSectionProps,
} from "./nutrition-kpi-section";

export type NutritionEntityCardProps = {
  accessory?: ReactNode;
  children?: ReactNode;
  density?: "compact" | "regular";
  entity: EntityKind;
  eyebrow?: string;
  indicators?: StructuralIndicator[];
  nutrition: Omit<NutritionKpiSectionProps, "density" | "style">;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
  subtitle?: string;
  title: string;
};

export function NutritionEntityCard({
  accessory,
  children,
  density = "regular",
  entity,
  eyebrow,
  indicators,
  nutrition,
  onPress,
  style,
  subtitle,
  title,
}: NutritionEntityCardProps) {
  return (
    <EntityCard
      accessory={accessory}
      entity={entity}
      eyebrow={eyebrow}
      indicators={indicators}
      onPress={onPress}
      style={style}
      subtitle={subtitle}
      title={title}>
      <View>
        <NutritionKpiSection density={density} {...nutrition} />
      </View>
      {children}
    </EntityCard>
  );
}
