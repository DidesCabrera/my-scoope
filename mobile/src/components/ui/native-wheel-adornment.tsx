import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { nativeWheelMetrics } from "./native-wheel-metrics";

export function NativeWheelAdornment({ label, width }: { label: string; width: number }) {
  return (
    <View pointerEvents="none" style={[styles.frame, { width }]}>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { alignItems: "center", height: nativeWheelMetrics.selectionRowHeight, justifyContent: "center" },
  label: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize, fontWeight: tokens.weight.medium, lineHeight: nativeWheelMetrics.selectionRowHeight },
});
