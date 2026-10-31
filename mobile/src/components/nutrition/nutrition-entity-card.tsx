import { type ReactNode, useState } from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import {
  EntityCard,
  EntityCardActions,
  EntityCardPanelToggle,
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
import { tokens } from "@/design/tokens";

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
  const panelToggleIcon = entity === "food" ? "information" : entity === "meal" ? "food" : entity === "program" ? "chart" : "meal";
  const panelToggleText = entity === "food" ? "Más información" : entity === "meal" ? "Alimentos" : entity === "program" ? "Semanas" : "Comidas";
  const panelToggleColor = entity === "food" || entity === "meal" ? tokens.color.food : entity === "dailyPlan" ? tokens.color.meal : tokens.color.dailyPlan;
  const panelToggle = hasCollapsiblePanel ? <EntityCardPanelToggle activeColor={panelToggleColor} expanded={panelExpanded} icon={panelToggleIcon} label={`detalles de ${title}`} onPress={() => setPanelExpanded((current) => !current)} text={panelToggleText} /> : undefined;
  const hasEntityIndicatorSpacing = Boolean(indicators?.length) && (entity === "food" || entity === "meal" || entity === "dailyPlan");
  const hasPanelSpacing = entity === "meal" || entity === "dailyPlan";
  return (
    <EntityCard
      accessory={accessory}
      actions={hasCollapsiblePanel ? undefined : actions}
      completion={completion}
      entity={entity}
      eyebrow={eyebrow}
      eyebrowAccessory={eyebrowAccessory}
      headingLink={headingLink}
      indicators={indicators}
      onPress={onPress}
      style={style}
      subtitle={subtitle}
      title={title}
      titleIcon={entity === "food" ? <FoodVisualIcon emoji={foodEmoji} name={title} size="title" visualKey={foodVisualKey} /> : undefined}>
      {showNutrition ? <View style={hasEntityIndicatorSpacing ? styles.nutritionAfterIndicators : undefined}>
        <NutritionKpiSection variant={kpiVariant} {...nutrition} />
      </View> : null}
      {afterNutrition}
      {hasCollapsiblePanel ? <View style={[styles.actionsBeforePanel, !panelExpanded && styles.actionsBeforePanelCollapsed]}><EntityCardActions leading={panelToggle}>{actions}</EntityCardActions></View> : null}
      {children && (!hasCollapsiblePanel || panelExpanded) ? <View style={hasCollapsiblePanel ? styles.panelAfterActions : showNutrition && hasPanelSpacing ? styles.panelsAfterNutrition : undefined}><EntityCardPanelSlot>{children}</EntityCardPanelSlot></View> : null}
    </EntityCard>
  );
}

const styles = StyleSheet.create({
  actionsBeforePanel: { marginTop: 2 },
  actionsBeforePanelCollapsed: { marginBottom: -2 },
  nutritionAfterIndicators: { marginTop: 4 },
  panelAfterActions: { marginTop: 2 },
  panelsAfterNutrition: { marginTop: 4 },
});
