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
  dailyPlanFoodsPanel?: ReactNode;
  supplementPanel?: ReactNode;
  supplementCompletion?: ReactNode;
  onLockedSupplementPress?: () => void;
  kpiVariant?: "nested" | "regular";
  entity: EntityKind;
  foodEmoji?: string | null;
  foodVisualKey?: string | null;
  initialPanelExpanded?: boolean;
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
  dailyPlanFoodsPanel,
  supplementPanel,
  supplementCompletion,
  onLockedSupplementPress,
  kpiVariant = "regular",
  entity,
  foodEmoji,
  foodVisualKey,
  initialPanelExpanded = false,
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
  const [panelExpanded, setPanelExpanded] = useState(initialPanelExpanded);
  const [foodsPanelExpanded, setFoodsPanelExpanded] = useState(false);
  const [supplementPanelExpanded, setSupplementPanelExpanded] = useState(false);
  const hasCollapsiblePanel = collapsiblePanel && Boolean(children);
  const hasDailyPlanFoodsPanel = hasCollapsiblePanel && entity === "dailyPlan" && Boolean(dailyPlanFoodsPanel);
  const hasSupplementPanel = collapsiblePanel && entity === "dailyPlan" && (Boolean(supplementPanel) || Boolean(onLockedSupplementPress));
  const anyPanelExpanded = panelExpanded || (hasDailyPlanFoodsPanel && foodsPanelExpanded) || supplementPanelExpanded;
  const panelToggleIcon = entity === "food" ? "information" : entity === "meal" || entity === "preparation" ? "food" : entity === "program" ? "chart" : "meal";
  const panelToggleText = entity === "food" ? "Más información" : entity === "meal" || entity === "preparation" ? "Alimentos" : entity === "program" ? "Semanas" : "Comidas";
  const panelToggleColor = entity === "food" || entity === "meal" || entity === "preparation" ? tokens.color.food : entity === "dailyPlan" ? tokens.color.meal : tokens.color.dailyPlan;
  function togglePanel() {
    const shouldExpand = !panelExpanded;
    setPanelExpanded(shouldExpand);
    if (shouldExpand && hasDailyPlanFoodsPanel) setFoodsPanelExpanded(false);
    if (shouldExpand) setSupplementPanelExpanded(false);
  }
  function toggleFoodsPanel() {
    const shouldExpand = !foodsPanelExpanded;
    setFoodsPanelExpanded(shouldExpand);
    if (shouldExpand) setPanelExpanded(false);
    if (shouldExpand) setSupplementPanelExpanded(false);
  }
  function toggleSupplementPanel() {
    if (onLockedSupplementPress) {
      onLockedSupplementPress();
      return;
    }
    const shouldExpand = !supplementPanelExpanded;
    setSupplementPanelExpanded(shouldExpand);
    if (shouldExpand) {
      setPanelExpanded(false);
      setFoodsPanelExpanded(false);
    }
  }
  const panelToggle = hasCollapsiblePanel ? <EntityCardPanelToggle activeColor={panelToggleColor} expanded={panelExpanded} icon={panelToggleIcon} label={`detalles de ${title}`} onPress={togglePanel} solidActive={hasDailyPlanFoodsPanel || entity === "food" || entity === "meal" || entity === "preparation"} text={panelToggleText} /> : undefined;
  const foodsPanelToggle = hasDailyPlanFoodsPanel ? <EntityCardPanelToggle activeColor={tokens.color.food} expanded={foodsPanelExpanded} icon="food" label={`alimentos de ${title}`} onPress={toggleFoodsPanel} solidActive text="Alimentos" /> : undefined;
  const supplementPanelToggle = hasSupplementPanel ? <EntityCardPanelToggle activeColor={tokens.color.supplement} activeForeground={tokens.color.entityIconForeground} expanded={supplementPanelExpanded} icon="supplement" label={`suplementos de ${title}`} onPress={toggleSupplementPanel} solidActive text="Sups" /> : undefined;
  const panelToggles = hasCollapsiblePanel ? <View style={styles.panelToggleGroup}>{panelToggle}{supplementPanelToggle}{foodsPanelToggle}</View> : undefined;
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
      titleIcon={entity === "food" ? <FoodVisualIcon emoji={foodEmoji} name={title} size="title" visualKey={foodVisualKey} /> : undefined}
      titleIconPosition={entity === "food" ? "trailing" : "leading"}>
      {showNutrition ? <View style={hasEntityIndicatorSpacing ? styles.nutritionAfterIndicators : undefined}>
        <NutritionKpiSection variant={kpiVariant} {...nutrition} />
      </View> : null}
      {afterNutrition ? supplementCompletion ? <View style={styles.completionStack}>{afterNutrition}{supplementCompletion}</View> : afterNutrition : supplementCompletion}
      {hasCollapsiblePanel ? <View style={[styles.actionsBeforePanel, !anyPanelExpanded && styles.actionsBeforePanelCollapsed]}><EntityCardActions leading={panelToggles}>{actions}</EntityCardActions></View> : null}
      {hasCollapsiblePanel && anyPanelExpanded ? <View style={[styles.panelAfterActions, styles.panelStack]}>
        {panelExpanded ? <EntityCardPanelSlot>{children}</EntityCardPanelSlot> : null}
        {hasDailyPlanFoodsPanel && foodsPanelExpanded ? <EntityCardPanelSlot>{dailyPlanFoodsPanel}</EntityCardPanelSlot> : null}
        {supplementPanelExpanded ? <EntityCardPanelSlot>{supplementPanel}</EntityCardPanelSlot> : null}
      </View> : null}
      {children && !hasCollapsiblePanel ? <View style={showNutrition && hasPanelSpacing ? styles.panelsAfterNutrition : undefined}><EntityCardPanelSlot>{children}</EntityCardPanelSlot></View> : null}
    </EntityCard>
  );
}

const styles = StyleSheet.create({
  actionsBeforePanel: { marginTop: 2 },
  actionsBeforePanelCollapsed: { marginBottom: -2 },
  completionStack: { gap: 8 },
  nutritionAfterIndicators: { marginTop: 4 },
  panelAfterActions: { marginTop: 2 },
  panelStack: { gap: tokens.spacing.sm },
  panelToggleGroup: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.compact },
  panelsAfterNutrition: { marginTop: 4 },
});
