import { type ComponentProps, type ReactNode, useState } from "react";
import { StyleSheet, View } from "react-native";

import { Card, Chip, EntityHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { FoodPanels } from "./entity-panels";

type GroupedFoodsCardProps = ComponentProps<typeof FoodPanels> & {
  title: string;
  chipsAction?: ReactNode;
  intro?: ReactNode;
  summaryChips?: ReactNode;
  showContents?: boolean;
};

export function GroupedFoodsCard({ chipsAction, items, preparation, preparationFirst = false, title, intro, summaryChips, showContents = true, ...panelProps }: GroupedFoodsCardProps) {
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
      {intro}
      {showContents ? <>
        <View style={[styles.chips, summaryChips ? styles.chipsWithSummary : null]}>
          <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={countLabel} textColor={tokens.color.textMain} />
          {summaryChips}
        </View>
        {chipsAction}
        <FoodPanels items={items} preparation={checklist} preparationFirst={preparationFirst} showPreparationColumn {...panelProps} />
      </> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  chips: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  chipsWithSummary: { marginTop: 8 - tokens.card.gap },
});
