import { type Href, usePathname, useRouter } from "expo-router";
import { ArrowUp, Sparkles } from "lucide-react-native";
import { useCallback, useMemo, useRef, useState } from "react";
import {
  Animated,
  Keyboard,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { useSession } from "@/auth/session-context";
import { ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { tokens } from "@/design/tokens";

import { stageAssistantQuickChatMessage } from "./assistant-quick-chat-draft";
import { clampQuickChatButtonOffset, nearestQuickChatHorizontalEdge, quickChatHorizontalEdgeForRelease } from "./assistant-quick-chat-position";
import { useAssistantQuickChatPreferences } from "./assistant-quick-chat-preferences";

const MAX_MESSAGE_LENGTH = 2000;
const FLOATING_BUTTON_SIZE = 58;
const FLOATING_BUTTON_EDGE_INSET = tokens.spacing.sm;

function AssistantGradientIcon() {
  return (
    <View style={styles.headerIcon}>
      <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
        <Defs>
          <LinearGradient id="assistant-quick-chat-header-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#assistant-quick-chat-header-macros)" height="100%" rx={tokens.radius.md} ry={tokens.radius.md} width="100%" />
      </Svg>
      <Sparkles color={tokens.color.surfaceApp} size={19} strokeWidth={2.4} />
    </View>
  );
}

export function AssistantQuickChatLauncher() {
  const inputRef = useRef<TextInput>(null);
  const [buttonOffset] = useState(() => new Animated.ValueXY());
  const insets = useSafeAreaInsets();
  const { height, width } = useWindowDimensions();
  const pathname = usePathname();
  const router = useRouter();
  const { profile, status } = useSession();
  const { ready: preferencesReady, showFloatingButton } = useAssistantQuickChatPreferences();
  const [message, setMessage] = useState("");
  const [visible, setVisible] = useState(false);

  const initialButtonBottom = Math.max(insets.bottom, tokens.spacing.md) + tokens.spacing.lg;
  const initialButtonLeft = width - tokens.spacing.lg - FLOATING_BUTTON_SIZE;
  const initialButtonTop = height - initialButtonBottom - FLOATING_BUTTON_SIZE;
  const dragBounds = useMemo(() => ({
    maximumX: width - Math.max(insets.right, FLOATING_BUTTON_EDGE_INSET) - FLOATING_BUTTON_SIZE - initialButtonLeft,
    maximumY: height - Math.max(insets.bottom, FLOATING_BUTTON_EDGE_INSET) - FLOATING_BUTTON_SIZE - initialButtonTop,
    minimumX: Math.max(insets.left, FLOATING_BUTTON_EDGE_INSET) - initialButtonLeft,
    minimumY: Math.max(insets.top, FLOATING_BUTTON_EDGE_INSET) - initialButtonTop,
  }), [height, initialButtonLeft, initialButtonTop, insets.bottom, insets.left, insets.right, insets.top, width]);

  const settleButton = useCallback((releaseX?: number) => {
    buttonOffset.flattenOffset();
    buttonOffset.stopAnimation(({ x, y }) => {
      Animated.spring(buttonOffset, {
        damping: 19,
        mass: 0.85,
        stiffness: 220,
        toValue: {
          x: releaseX == null
            ? nearestQuickChatHorizontalEdge(x, dragBounds.minimumX, dragBounds.maximumX)
            : quickChatHorizontalEdgeForRelease(releaseX, width, dragBounds.minimumX, dragBounds.maximumX),
          y: clampQuickChatButtonOffset(y, dragBounds.minimumY, dragBounds.maximumY),
        },
        useNativeDriver: false,
      }).start();
    });
  }, [buttonOffset, dragBounds, width]);

  const dragResponder = useMemo(() => PanResponder.create({
    onMoveShouldSetPanResponder: (_event, gesture) => Math.hypot(gesture.dx, gesture.dy) > 4,
    onPanResponderGrant: () => {
      buttonOffset.stopAnimation();
      buttonOffset.extractOffset();
    },
    onPanResponderMove: Animated.event([null, { dx: buttonOffset.x, dy: buttonOffset.y }], { useNativeDriver: false }),
    onPanResponderRelease: (_event, gesture) => settleButton(gesture.moveX),
    onPanResponderTerminate: () => settleButton(),
  }), [buttonOffset, settleButton]);

  const available = status === "authenticated"
    && preferencesReady
    && showFloatingButton
    && Boolean(profile?.onboarding_completed)
    && !profile?.review_disclosure_required
    && !pathname.startsWith("/assistant")
    && !pathname.startsWith("/proposals");

  if (!available) return null;

  const close = () => {
    Keyboard.dismiss();
    setVisible(false);
    setMessage("");
  };

  const open = () => {
    setMessage("");
    setVisible(true);
  };

  const submit = () => {
    const normalized = message.trim();
    if (!normalized) return;
    stageAssistantQuickChatMessage(normalized);
    Keyboard.dismiss();
    setVisible(false);
    setMessage("");
    router.push("/assistant/new" as Href);
  };

  return (
    <View pointerEvents="box-none" style={styles.overlay}>
      <View style={[styles.floatingButtonPositioner, { bottom: initialButtonBottom, right: tokens.spacing.lg }]}>
        <Animated.View
          {...dragResponder.panHandlers}
          style={[styles.floatingButtonFrame, { transform: buttonOffset.getTranslateTransform() }]}>
          <Pressable
            accessibilityHint="Toca para abrir o arrastra para mover"
            accessibilityLabel="Abrir chat rápido con el Asistente"
            accessibilityRole="button"
            hitSlop={8}
            onPress={open}
            style={({ pressed }) => [styles.floatingButton, pressed && styles.floatingButtonPressed]}>
            <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
              <Defs>
                <LinearGradient id="assistant-quick-chat-macros" x1="0" x2="1" y1="0" y2="1">
                  <Stop offset="0" stopColor={tokens.color.protein} />
                  <Stop offset="0.5" stopColor={tokens.color.carbs} />
                  <Stop offset="1" stopColor={tokens.color.fat} />
                </LinearGradient>
              </Defs>
              <Rect fill="url(#assistant-quick-chat-macros)" height="100%" rx={30} ry={30} width="100%" />
            </Svg>
            <Sparkles color={tokens.color.surfaceApp} size={25} strokeWidth={2} />
          </Pressable>
        </Animated.View>
      </View>

      <ActionSheetModal onRequestClose={close} visible={visible}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
          <ActionSheetHeader iconNode={<AssistantGradientIcon />} onClose={close} title="Pregunta al Asistente" />
          <View style={styles.sheetContent}>
            <Text style={styles.inputLabel}>Mensaje</Text>
            <View style={styles.inputRow}>
              <TextInput
                accessibilityLabel="Mensaje para el Asistente"
                autoCapitalize="sentences"
                autoCorrect
                autoFocus
                maxLength={MAX_MESSAGE_LENGTH}
                onChangeText={setMessage}
                onSubmitEditing={submit}
                placeholder="Escribe tu mensaje"
                placeholderTextColor={tokens.color.textSubtle}
                ref={inputRef}
                returnKeyType="send"
                selectionColor={tokens.color.interactivePrimary}
                style={styles.input}
                value={message}
              />
              <Pressable
                accessibilityLabel="Iniciar conversación"
                accessibilityRole="button"
                accessibilityState={{ disabled: !message.trim() }}
                disabled={!message.trim()}
                onPress={submit}
                style={({ pressed }) => [styles.sendButton, !message.trim() && styles.sendButtonDisabled, pressed && styles.sendButtonPressed]}>
                <ArrowUp color={tokens.color.surfaceApp} size={20} strokeWidth={3} />
              </Pressable>
            </View>
          </View>
        </SafeAreaView>
      </ActionSheetModal>
    </View>
  );
}

const styles = StyleSheet.create({
  floatingButton: {
    alignItems: "center",
    borderRadius: 30,
    height: "100%",
    justifyContent: "center",
    overflow: "hidden",
    width: "100%",
  },
  floatingButtonFrame: {
    elevation: 8,
    height: FLOATING_BUTTON_SIZE,
    shadowColor: "#000000",
    shadowOffset: { height: 4, width: 0 },
    shadowOpacity: 0.22,
    shadowRadius: 9,
    width: FLOATING_BUTTON_SIZE,
  },
  floatingButtonPositioner: { height: FLOATING_BUTTON_SIZE, position: "absolute", width: FLOATING_BUTTON_SIZE },
  floatingButtonPressed: { opacity: 0.78, transform: [{ scale: 0.96 }] },
  headerIcon: { alignItems: "center", borderRadius: tokens.radius.md, height: 36, justifyContent: "center", overflow: "hidden", width: 36 },
  input: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, minHeight: 44, paddingHorizontal: tokens.spacing.md, paddingVertical: 0 },
  inputLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  inputRow: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.card, flexDirection: "row", gap: tokens.spacing.sm, padding: 6 },
  overlay: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0, zIndex: 20 },
  sheetContent: { gap: tokens.spacing.sm, paddingHorizontal: tokens.spacing.screen, paddingBottom: 10, paddingTop: tokens.spacing.compact },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sendButton: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.pill, height: 40, justifyContent: "center", width: 40 },
  sendButtonDisabled: { opacity: 0.35 },
  sendButtonPressed: { opacity: 0.72, transform: [{ scale: 0.96 }] },
});
