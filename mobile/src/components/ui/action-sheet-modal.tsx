import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react-native";
import { X } from "lucide-react-native";
import { BlurView } from "expo-blur";
import { requireOptionalNativeModule } from "expo-modules-core";
import {
  Animated,
  Easing,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { initialWindowMetrics, useSafeAreaInsets } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";
import { EntityIcon, SectionIcon, type EntityKind, type SectionKind } from "./product";

type ActionSheetModalProps = PropsWithChildren<{
  dismissImmediately?: boolean;
  onDismiss?(): void;
  onRequestClose(): void;
  visible: boolean;
}>;

const nativeBlurAvailable = Boolean(requireOptionalNativeModule("ExpoBlur"));

export function ModalBackdrop({ accessibilityLabel, onPress }: { accessibilityLabel: string; onPress(): void }) {
  return (
    <>
      {nativeBlurAvailable ? <BlurView intensity={38} style={StyleSheet.absoluteFill} tint="dark" /> : null}
      <View style={styles.scrimTint} />
      <Pressable accessibilityLabel={accessibilityLabel} onPress={onPress} style={styles.scrimPressable} />
    </>
  );
}

export function ActionSheetModal({ children, dismissImmediately = false, onDismiss, onRequestClose, visible }: ActionSheetModalProps) {
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

    if (dismissImmediately) {
      scrimOpacity.setValue(0);
      sheetTranslateY.setValue(hiddenSheetOffset);
      requestAnimationFrame(() => {
        setMounted(false);
        onDismiss?.();
      });
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
      if (finished) {
        setMounted(false);
        onDismiss?.();
      }
    });
  }, [dismissImmediately, hiddenSheetOffset, mounted, onDismiss, scrimOpacity, sheetTranslateY, visible]);

  return (
    <Modal
      animationType="none"
      navigationBarTranslucent
      onRequestClose={onRequestClose}
      presentationStyle="overFullScreen"
      statusBarTranslucent
      transparent
      visible={mounted}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.modalRoot}>
        <Animated.View pointerEvents={visible ? "auto" : "none"} style={[styles.scrim, { opacity: scrimOpacity }]}>
          <ModalBackdrop accessibilityLabel="Cerrar acciones" onPress={onRequestClose} />
        </Animated.View>
        <Animated.View
          style={[styles.sheetFrame, { paddingBottom: bottomInset, transform: [{ translateY: sheetTranslateY }] }]}
        >
          <View style={styles.sheetHandle} />
          {children}
        </Animated.View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export function ActionSheetHeader({ entity, icon: Icon, iconColor = tokens.color.textMain, onClose, section, title }: { entity?: EntityKind; icon?: LucideIcon; iconColor?: string; onClose(): void; section?: SectionKind; title: string }) {
  return (
    <View style={styles.header}>
      <View style={styles.headerIdentity}>
        {entity ? <EntityIcon entity={entity} size="header" /> : section ? <SectionIcon section={section} /> : Icon ? <Icon color={iconColor} size={24} strokeWidth={2.1} /> : null}
        <Text numberOfLines={2} style={styles.headerTitle}>{title}</Text>
      </View>
      <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={onClose} style={({ pressed }) => [styles.close, pressed && styles.pressed]}>
        <X color={tokens.color.textMain} size={22} />
      </Pressable>
    </View>
  );
}

export function ActionSheetActions({ children }: PropsWithChildren) {
  return (
    <View>
      <Text style={styles.actionsEyebrow}>ACCIONES</Text>
      <View style={styles.actionsTable}>{children}</View>
    </View>
  );
}

export function ActionSheetAction({ destructive = false, disabled = false, icon: Icon, label, onPress }: { destructive?: boolean; disabled?: boolean; icon: LucideIcon; label: string; onPress(): void }) {
  const color = destructive ? tokens.color.danger : tokens.color.textMain;
  return (
    <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.actionRow, (pressed || disabled) && styles.pressed]}>
      <View style={styles.actionIcon}><Icon color={color} size={18} /></View>
      <Text style={[styles.actionLabel, destructive && styles.actionLabelDanger]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 15, fontWeight: tokens.weight.medium },
  actionLabelDanger: { color: tokens.color.danger },
  actionIcon: { alignItems: "center", justifyContent: "center", width: 20 },
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: StyleSheet.hairlineWidth, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingHorizontal: tokens.spacing.lg },
  actionsEyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1, marginBottom: tokens.spacing.sm },
  actionsTable: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden" },
  close: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  header: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  headerIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.md, minWidth: 0 },
  headerTitle: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  modalRoot: { flex: 1, justifyContent: "flex-end" },
  pressed: { opacity: 0.65 },
  scrim: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  scrimPressable: { flex: 1 },
  scrimTint: { backgroundColor: "rgba(0, 0, 0, 0.36)", bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  sheetFrame: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, overflow: "hidden", width: "100%" },
  sheetHandle: { alignSelf: "center", backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 4, marginTop: tokens.spacing.sm, width: 40 },
});
