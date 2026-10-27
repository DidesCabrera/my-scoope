import { useId } from "react";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

export function CalendarTodayOutline({ cornerRadius = 9, filled = false, height, width }: { cornerRadius?: number; filled?: boolean; height: number; width: number }) {
  const gradientId = useId().replace(/:/g, "");
  if (width <= 0 || height <= 0) return null;
  return <Svg height={height} pointerEvents="none" style={{ left: 0, position: "absolute", top: 0 }} width={width}>
    <Defs>
      <LinearGradient id={gradientId} x1="0" x2="1" y1="1" y2="0">
        <Stop offset="0" stopColor={tokens.color.protein} />
        <Stop offset="0.5" stopColor={tokens.color.carbs} />
        <Stop offset="1" stopColor={tokens.color.fat} />
      </LinearGradient>
    </Defs>
    {filled
      ? <Rect fill={`url(#${gradientId})`} height={height} rx={cornerRadius} width={width} />
      : <Rect fill="none" height={height - 2} rx={cornerRadius} stroke={`url(#${gradientId})`} strokeWidth={2} width={width - 2} x={1} y={1} />}
  </Svg>;
}
