import { useState, type ReactNode } from "react";
import { ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

export function HalfHeightScrollablePhoto({ children, surfaceStyle }: { children: ReactNode; surfaceStyle?: StyleProp<ViewStyle> }) {
  const [contentWidth, setContentWidth] = useState(0);
  const photoSize = contentWidth ? contentWidth + tokens.spacing.screen * 2 : 0;

  return (
    <View
      onLayout={({ nativeEvent }) => setContentWidth((current) => current === nativeEvent.layout.width ? current : nativeEvent.layout.width)}
      style={[styles.layout, photoSize ? { height: photoSize / 2 } : styles.fallback]}>
      {photoSize ? (
        <ScrollView
          accessibilityLabel="Desplazar etiqueta nutricional verticalmente"
          bounces={false}
          contentContainerStyle={{ height: photoSize }}
          directionalLockEnabled
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
          style={[styles.viewport, { height: photoSize / 2, width: photoSize }]}>
          <View style={[styles.surface, surfaceStyle, { height: photoSize, width: photoSize }]}>{children}</View>
        </ScrollView>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  layout: { marginTop: -tokens.spacing.lg, position: "relative" },
  fallback: { aspectRatio: 2 },
  viewport: { left: -tokens.spacing.screen, position: "absolute", top: 0 },
  surface: { overflow: "hidden" },
});
