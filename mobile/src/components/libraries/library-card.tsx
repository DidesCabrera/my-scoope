import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import type { LibraryActionResult, LibraryItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { FoodPanels, MealPanels, ProgramPanels } from "./entity-panels";
import { libraryNutrition } from "./presentation-adapters";
import { ProgramChildCard, programDailyMetricData } from "./program-child-card";
import { LibraryActions } from "./library-actions";

function indicatorValue(item: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = item.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function LibraryCard({ apiRequest, interactive = true, item, onChanged }: { apiRequest: ApiRequest; interactive?: boolean; item: LibraryItem; onChanged(result: LibraryActionResult): void }) {
  const router = useRouter();
  const segment = item.entity === "dailyPlan" ? "daily-plans" : item.entity === "program" ? "programs" : item.entity === "meal" ? "meals" : "foods";
  const detailHref = `/libraries/${segment}/${item.id}` as Href;
  if (item.entity === "program") {
    const metrics = item.panel.kind === "weeks" ? programDailyMetricData(item.panel.weeks) : [];
    const card = (onMore?: () => void) => (
      <ProgramChildCard
        axisLabels={item.panel.kind === "weeks" ? item.panel.weeks.map((week) => `S${week.week_number}`) : []}
        filledDaysCount={indicatorValue(item, "dailyPlan")}
        foodsCount={indicatorValue(item, "food")}
        metricData={metrics}
        onMore={onMore}
        onOpen={interactive ? () => router.push(detailHref) : undefined}
        owner={item.creator}
        title={item.name}
        weeksCount={indicatorValue(item, "week")}
      />
    );
    if (!interactive) return card();
    return item.actions?.length ? (
      <LibraryActions apiRequest={apiRequest} entitySlug={segment} item={item} onCompleted={onChanged} renderTrigger={(open) => card(open)} />
    ) : card();
  }
  return (
    <NutritionEntityCard actions={interactive ? <>{item.actions?.length ? <LibraryActions apiRequest={apiRequest} entitySlug={segment} item={item} onCompleted={onChanged} /> : null}<EntityCardAction label={`Ver detalle de ${item.name}`} onPress={() => router.push(detailHref)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction></> : undefined} entity={item.entity} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} subtitle={item.subtitle || undefined} title={item.name}>
      {item.panel.kind === "foods" ? <FoodPanels items={item.panel.foods} /> : null}
      {item.panel.kind === "meals" ? <MealPanels items={item.panel.meals} /> : null}
      {item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}
    </NutritionEntityCard>
  );
}
