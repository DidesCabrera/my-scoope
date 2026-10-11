import { Sparkles } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

export function AssistantGradientIcon({ size = 22, strokeWidth = 2.4 }: { size?: number; strokeWidth?: number }) {
  const glyphSize = size * (13 / 22);
  return (
    <View style={{ alignItems: "center", height: size, justifyContent: "center", overflow: "hidden", width: size, borderRadius: size * (5 / 22) }}>
      <Svg aria-hidden height={size} pointerEvents="none" style={StyleSheet.absoluteFill} width={size}>
        <Defs>
          <LinearGradient id={`assistant-gradient-${size}`} x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill={`url(#assistant-gradient-${size})`} height={size} rx={size * (5 / 22)} ry={size * (5 / 22)} width={size} />
      </Svg>
      <Sparkles color={tokens.color.surfaceApp} size={glyphSize} strokeWidth={strokeWidth} />
    </View>
  );
}
