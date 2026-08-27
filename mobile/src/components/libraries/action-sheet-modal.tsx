import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import {
  Animated,
  Dimensions,
  Easing,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
} from "react-native";

type ActionSheetModalProps = PropsWithChildren<{
  onRequestClose(): void;
  visible: boolean;
}>;

const hiddenSheetOffset = Dimensions.get("window").height;

export function ActionSheetModal({ children, onRequestClose, visible }: ActionSheetModalProps) {
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
  }, [mounted, scrimOpacity, sheetTranslateY, visible]);

  return (
    <Modal
      animationType="none"
      onRequestClose={onRequestClose}
      presentationStyle="overFullScreen"
      statusBarTranslucent
      transparent
      visible={mounted}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.modalRoot}>
        <Animated.View pointerEvents={visible ? "auto" : "none"} style={[styles.scrim, { opacity: scrimOpacity }]}>
          <Pressable accessibilityLabel="Cerrar acciones" onPress={onRequestClose} style={styles.scrimPressable} />
        </Animated.View>
        <Animated.View style={{ transform: [{ translateY: sheetTranslateY }] }}>
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
});
