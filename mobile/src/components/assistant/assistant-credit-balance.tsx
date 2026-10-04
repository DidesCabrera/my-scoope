import { useState } from "react";
import { LayoutChangeEvent, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

export function AssistantCreditBalance({ availability, contained = false }: { availability: { available_credits: number }; contained?: boolean }) {
  const { width } = useWindowDimensions();
  const [panelSize, setPanelSize] = useState({ height: 0, width: 0 });

  const handlePanelLayout = (event: LayoutChangeEvent) => {
    const { height, width: panelWidth } = event.nativeEvent.layout;
    if (height !== panelSize.height || panelWidth !== panelSize.width) {
      setPanelSize({ height, width: panelWidth });
    }
  };

  const panel = (
    <View onLayout={handlePanelLayout} style={[styles.panel, contained ? styles.panelContainedSurface : styles.panelStandalone, !contained && { width: Math.max(0, width - (tokens.layout.reducedInset * 2)) }]}> 
      {panelSize.width > 0 && panelSize.height > 0 ? <Svg aria-hidden height={panelSize.height} pointerEvents="none" style={StyleSheet.absoluteFill} width={panelSize.width}>
        <Defs>
          <LinearGradient id="assistant-credit-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#assistant-credit-macros)" height={panelSize.height} width={panelSize.width} />
      </Svg> : null}
      <View accessibilityLabel={`${availability.available_credits} créditos disponibles`} accessible style={styles.balance}>
        <Text style={styles.value}>{availability.available_credits}</Text>
        <Text style={styles.label}>créditos disponibles</Text>
      </View>
    </View>
  );

  return contained ? <View style={styles.panelContained}>{panel}</View> : panel;
}

const styles = StyleSheet.create({
  balance: { alignItems: "center", alignSelf: "stretch", flex: 1, flexDirection: "row", flexShrink: 1, gap: tokens.spacing.xs, minWidth: 0, paddingHorizontal: tokens.card.outerPadding, paddingVertical: tokens.spacing.sm },
  label: { color: tokens.color.surfaceApp, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, lineHeight: 18 },
  panel: { alignItems: "center", alignSelf: "stretch", borderColor: tokens.color.surfaceApp, borderRadius: tokens.radius.panel, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", marginBottom: tokens.spacing.sm, minHeight: 54, minWidth: 0, overflow: "hidden" },
  panelContained: { alignSelf: "stretch", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  panelContainedSurface: { marginBottom: 0 },
  panelStandalone: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  value: { color: tokens.color.surfaceApp, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 22 },
});
