import type { ComponentProps } from "react";

import { Card, Chip, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { FoodPanels } from "./entity-panels";

type GroupedFoodsCardProps = ComponentProps<typeof FoodPanels> & {
  title: string;
};

export function GroupedFoodsCard({ items, title, ...panelProps }: GroupedFoodsCardProps) {
  const countLabel = `${items.length} ${items.length === 1 ? "alimento" : "alimentos"}`;
  return (
    <Card accent={tokens.color.food}>
      <EntityHeading entity="food" eyebrow="LISTA DE ALIMENTOS" title={title} />
      <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={countLabel} textColor={tokens.color.textMain} />
      <FoodPanels items={items} {...panelProps} />
    </Card>
  );
}
