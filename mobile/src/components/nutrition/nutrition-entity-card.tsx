import type { ReactNode } from "react";
import { StyleProp, View, ViewStyle } from "react-native";

import {
  EntityCard,
  EntityCardPanelSlot,
  type EntityKind,
  type StructuralIndicator,
} from "@/components/ui";
import {
  NutritionKpiSection,
  type NutritionKpiSectionProps,
} from "./nutrition-kpi-section";

export type NutritionEntityCardProps = {
  accessory?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  kpiVariant?: "nested" | "regular";
  entity: EntityKind;
  eyebrow?: string;
  indicators?: StructuralIndicator[];
  nutrition: Omit<NutritionKpiSectionProps, "style" | "variant">;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
  subtitle?: string;
  title: string;
};

export function NutritionEntityCard({
  accessory,
  actions,
  children,
  kpiVariant = "regular",
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
      actions={actions}
      entity={entity}
      eyebrow={eyebrow}
      indicators={indicators}
      onPress={onPress}
      style={style}
      subtitle={subtitle}
      title={title}>
      <View>
        <NutritionKpiSection variant={kpiVariant} {...nutrition} />
      </View>
      {children ? <EntityCardPanelSlot>{children}</EntityCardPanelSlot> : null}
    </EntityCard>
  );
}
