import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import {
  Animated,
  Easing,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  useWindowDimensions,
} from "react-native";
import { initialWindowMetrics, useSafeAreaInsets } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";

type ActionSheetModalProps = PropsWithChildren<{
  onRequestClose(): void;
  visible: boolean;
}>;

export function ActionSheetModal({ children, onRequestClose, visible }: ActionSheetModalProps) {
  const { height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const bottomInset = Math.max(insets.bottom, initialWindowMetrics?.insets.bottom ?? 0);
  const hiddenSheetOffset = height;
  const [mounted, setMounted] = useState(visible);
  const [scrimOpacity] = useState(() => new Animated.Value(visible ? 1 : 0));
  const [sheetTranslateY] = useState(() => new Animated.Value(visible ? 0 : hiddenSheetOffset));

  useEffect(() => {
    if (!visible || mounted) return;
    const frame = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(frame);
  }, [mounted, visible]);

  useEffect(() => {
    if (!mounted) return;

    scrimOpacity.stopAnimation();
    sheetTranslateY.stopAnimation();

    if (visible) {
      scrimOpacity.setValue(0);
      sheetTranslateY.setValue(hiddenSheetOffset);
      Animated.parallel([
        Animated.timing(scrimOpacity, {
          duration: 190,
          easing: Easing.out(Easing.quad),
          toValue: 1,
          useNativeDriver: true,
        }),
        Animated.timing(sheetTranslateY, {
          duration: 280,
          easing: Easing.out(Easing.cubic),
          toValue: 0,
          useNativeDriver: true,
        }),
      ]).start();
      return;
    }

    Animated.parallel([
      Animated.timing(scrimOpacity, {
        duration: 180,
        easing: Easing.in(Easing.quad),
        toValue: 0,
        useNativeDriver: true,
      }),
      Animated.timing(sheetTranslateY, {
        duration: 240,
        easing: Easing.in(Easing.cubic),
        toValue: hiddenSheetOffset,
        useNativeDriver: true,
      }),
    ]).start(({ finished }) => {
      if (finished) setMounted(false);
    });
  }, [hiddenSheetOffset, mounted, scrimOpacity, sheetTranslateY, visible]);

  return (
    <Modal
      animationType="none"
      navigationBarTranslucent
      onRequestClose={onRequestClose}
      presentationStyle="overFullScreen"
      statusBarTranslucent
      transparent
      visible={mounted}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalRoot}>
        <Animated.View pointerEvents={visible ? "auto" : "none"} style={[styles.scrim, { opacity: scrimOpacity }]}>
          <Pressable accessibilityLabel="Cerrar acciones" onPress={onRequestClose} style={styles.scrimPressable} />
        </Animated.View>
        <Animated.View style={[styles.sheetFrame, { paddingBottom: bottomInset, transform: [{ translateY: sheetTranslateY }] }]}>
          {children}
        </Animated.View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalRoot: { flex: 1, justifyContent: "flex-end" },
  scrim: { backgroundColor: "rgba(20, 24, 22, 0.42)", bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  scrimPressable: { flex: 1 },
  sheetFrame: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, overflow: "hidden", width: "100%" },
});
