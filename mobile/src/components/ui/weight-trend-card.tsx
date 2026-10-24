import type { WeightItem } from "@/api/types";

import { CardHeader } from "./product";
import { Card } from "./surfaces";
import { WeightTrendChart } from "./weight-trend-chart";

export function WeightTrendCard({ items }: { items: WeightItem[] }) {
  return <Card>
    <CardHeader description={`${items.length} registros`} title="Tendencia de peso" />
    <WeightTrendChart items={items} />
  </Card>;
}
