import { type ComponentProps, useState } from "react";

import { Card, Chip, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { FoodPanels } from "./entity-panels";

type GroupedFoodsCardProps = ComponentProps<typeof FoodPanels> & {
  title: string;
};

export function GroupedFoodsCard({ items, preparation, title, ...panelProps }: GroupedFoodsCardProps) {
  const [checkedIds, setCheckedIds] = useState<Set<string>>(() => new Set());
  const countLabel = `${items.length} ${items.length === 1 ? "alimento" : "alimentos"}`;
  const checklist = preparation ?? {
    isPrepared: (item: (typeof items)[number]) => checkedIds.has(item.id),
    onToggle: (item: (typeof items)[number]) => setCheckedIds((current) => {
      const next = new Set(current);
      if (next.has(item.id)) next.delete(item.id);
      else next.add(item.id);
      return next;
    }),
  };
  return (
    <Card accent={tokens.color.food}>
      <EntityHeading entity="food" eyebrow="LISTA DE ALIMENTOS" title={title} />
      <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={countLabel} textColor={tokens.color.textMain} />
      <FoodPanels items={items} preparation={checklist} {...panelProps} />
    </Card>
  );
}
