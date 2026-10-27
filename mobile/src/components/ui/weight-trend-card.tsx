import type { WeightItem } from "@/api/types";
import { ChartLine } from "lucide-react-native";
import { View } from "react-native";

import { tokens } from "@/design/tokens";

import { CardHeader, GuideMetric } from "./product";
import { Card } from "./surfaces";
import { WeightTrendChart } from "./weight-trend-chart";

export function WeightTrendCard({ items, marginHorizontal, chartMarginLeft = 0, chartMarginRight = 0, yAxisLabelInset = 0, currentWeightLabel, onPressCurrentWeight }: { items: WeightItem[]; marginHorizontal?: number; chartMarginLeft?: number; chartMarginRight?: number; yAxisLabelInset?: number; currentWeightLabel?: string; onPressCurrentWeight?: () => void }) {
  return <Card style={marginHorizontal === undefined ? undefined : { marginHorizontal }}>
    <CardHeader accessory={currentWeightLabel ? <GuideMetric onPress={onPressCurrentWeight} tone="ppk" value={currentWeightLabel} /> : undefined} description={`${items.length} registros`} leadingIcon={<ChartLine color={tokens.color.textMain} size={23} strokeWidth={2.1} />} title="Tendencia de peso" />
    <View style={{ marginLeft: chartMarginLeft, marginRight: chartMarginRight }}>
      <WeightTrendChart items={items} yAxisLabelInset={yAxisLabelInset} />
    </View>
  </Card>;
}
