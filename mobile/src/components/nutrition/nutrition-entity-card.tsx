import { type ReactNode, useState } from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

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
import { FoodVisualIcon } from "./food-visual-icon";

export type NutritionEntityCardProps = {
  accessory?: ReactNode;
  actions?: ReactNode;
  afterNutrition?: ReactNode;
  children?: ReactNode;
  collapsiblePanel?: boolean;
  completion?: CompletionIndicatorCounts;
  kpiVariant?: "nested" | "regular";
  entity: EntityKind;
  foodEmoji?: string | null;
  foodVisualKey?: string | null;
  eyebrow?: string;
  eyebrowAccessory?: ReactNode;
  headingLink?: EntityHeadingLink;
  indicators?: StructuralIndicator[];
  nutrition: Omit<NutritionKpiSectionProps, "style" | "variant">;
  onPress?: () => void;
  showNutrition?: boolean;
  style?: StyleProp<ViewStyle>;
  subtitle?: string;
  title: string;
};

export function NutritionEntityCard({
  accessory,
  actions,
  afterNutrition,
  children,
  collapsiblePanel = false,
  completion,
  kpiVariant = "regular",
  entity,
  foodEmoji,
  foodVisualKey,
  eyebrow,
  eyebrowAccessory,
  headingLink,
  indicators,
  nutrition,
  onPress,
  showNutrition = true,
  style,
  subtitle,
  title,
}: NutritionEntityCardProps) {
  const [panelExpanded, setPanelExpanded] = useState(true);
  const hasCollapsiblePanel = collapsiblePanel && Boolean(children);
  const hasEntityIndicatorSpacing = Boolean(indicators?.length) && (entity === "food" || entity === "meal" || entity === "dailyPlan");
  const hasPanelSpacing = entity === "meal" || entity === "dailyPlan";
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
      panelToggle={hasCollapsiblePanel ? { expanded: panelExpanded, label: `detalles de ${title}`, onPress: () => setPanelExpanded((current) => !current) } : undefined}
      style={style}
      subtitle={subtitle}
      title={title}
      titleIcon={entity === "food" ? <FoodVisualIcon emoji={foodEmoji} name={title} size="title" visualKey={foodVisualKey} /> : undefined}>
      {showNutrition ? <View style={hasEntityIndicatorSpacing ? styles.nutritionAfterIndicators : undefined}>
        <NutritionKpiSection variant={kpiVariant} {...nutrition} />
      </View> : null}
      {afterNutrition}
      {children && (!hasCollapsiblePanel || panelExpanded) ? <View style={showNutrition && hasPanelSpacing ? styles.panelsAfterNutrition : undefined}><EntityCardPanelSlot>{children}</EntityCardPanelSlot></View> : null}
    </EntityCard>
  );
}

const styles = StyleSheet.create({
  nutritionAfterIndicators: { marginTop: 4 },
  panelsAfterNutrition: { marginTop: 4 },
});
