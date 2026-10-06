import type { ReactNode } from "react";
import { StyleProp, View, ViewStyle } from "react-native";

import {
  EntityCard,
  EntityCardPanelSlot,
  type CompletionIndicatorCounts,
  type EntityHeadingLink,
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
  afterNutrition?: ReactNode;
  children?: ReactNode;
  completion?: CompletionIndicatorCounts;
  kpiVariant?: "nested" | "regular";
  entity: EntityKind;
  eyebrow?: string;
  eyebrowAccessory?: ReactNode;
  headingLink?: EntityHeadingLink;
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
  afterNutrition,
  children,
  completion,
  kpiVariant = "regular",
  entity,
  eyebrow,
  eyebrowAccessory,
  headingLink,
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
      completion={completion}
      entity={entity}
      eyebrow={eyebrow}
      eyebrowAccessory={eyebrowAccessory}
      headingLink={headingLink}
      indicators={indicators}
      onPress={onPress}
      style={style}
      subtitle={subtitle}
      title={title}>
      <View>
        <NutritionKpiSection variant={kpiVariant} {...nutrition} />
      </View>
      {afterNutrition}
      {children ? <EntityCardPanelSlot>{children}</EntityCardPanelSlot> : null}
    </EntityCard>
  );
}
