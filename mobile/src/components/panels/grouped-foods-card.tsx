import type { ComponentProps } from "react";

import { Card, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { FoodPanels } from "./entity-panels";

type GroupedFoodsCardProps = ComponentProps<typeof FoodPanels> & {
  title: string;
};

export function GroupedFoodsCard({ title, ...panelProps }: GroupedFoodsCardProps) {
  return (
    <Card accent={tokens.color.food}>
      <EntityHeading entity="food" eyebrow="Alimentos agrupados" title={title} />
      <FoodPanels {...panelProps} />
    </Card>
  );
}
