import { useEffect, useState } from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

const beamHeight = 3;
const travelDurationMs = 2800;

export function AnimatedScanBeam({ gradientId }: { gradientId: string }) {
  const [progress] = useState(() => new Animated.Value(0));
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (height <= beamHeight) return undefined;
    progress.setValue(0);
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(progress, { duration: travelDurationMs, easing: Easing.linear, toValue: 1, useNativeDriver: true }),
      Animated.timing(progress, { duration: travelDurationMs, easing: Easing.linear, toValue: 0, useNativeDriver: true }),
    ]));
    animation.start();
    return () => animation.stop();
  }, [height, progress]);

  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      onLayout={({ nativeEvent }) => setHeight(nativeEvent.layout.height)}
      pointerEvents="none"
      style={StyleSheet.absoluteFill}
    >
      <Animated.View style={[styles.beam, {
        transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [0, Math.max(0, height - beamHeight)] }) }],
      }]}>
        <Svg aria-hidden height="100%" width="100%">
          <Defs>
            <LinearGradient id={gradientId} x1="0" x2="1" y1="0" y2="0">
              <Stop offset="0" stopColor={tokens.color.protein} />
              <Stop offset="0.5" stopColor={tokens.color.carbs} />
              <Stop offset="1" stopColor={tokens.color.fat} />
            </LinearGradient>
          </Defs>
          <Rect fill={`url(#${gradientId})`} height="100%" width="100%" />
        </Svg>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  beam: { height: beamHeight, left: 0, overflow: "hidden", position: "absolute", right: 0, top: 0 },
});
