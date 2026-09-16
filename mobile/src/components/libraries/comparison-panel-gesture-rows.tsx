import { Fragment, type ReactNode, useRef, useState } from "react";
import * as Haptics from "expo-haptics";
import { Pressable, type StyleProp, StyleSheet, View, type ViewStyle } from "react-native";
import { NestableDraggableFlatList, ScaleDecorator, type RenderItemParams } from "react-native-draggable-flatlist";
import ReanimatedSwipeable, { SwipeDirection, type SwipeableMethods } from "react-native-gesture-handler/ReanimatedSwipeable";
import Animated, { type SharedValue, useAnimatedStyle, useSharedValue } from "react-native-reanimated";

import { tokens } from "@/design/tokens";

export type ComparisonPanelAction = {
  backgroundColor: string;
  icon: ReactNode;
  label: string;
  onPress(): void;
};

type ComparisonPanelGestureRowsProps<T extends { id: string }> = {
  actions(item: T): ComparisonPanelAction[];
  itemLabel(item: T): string;
  items: T[];
  onReorder(items: T[]): Promise<void>;
  renderRow(item: T, index: number): ReactNode;
};

export function beginComparisonPanelDrag(drag: () => void) {
  void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid).catch(() => undefined);
  drag();
}

function DirectionalSwipeSurface({ children, direction, progress, side, style }: { children: ReactNode; direction: SharedValue<number>; progress: SharedValue<number>; side: "left" | "right"; style: StyleProp<ViewStyle> }) {
  const visibilityStyle = useAnimatedStyle(() => ({
    opacity: progress.value > 0 && direction.value === (side === "left" ? 1 : -1) ? 1 : 0,
  }), [direction, progress, side]);
  return <Animated.View style={[style, visibilityStyle]}>{children}</Animated.View>;
}

function GestureRow<T extends { id: string }>({ actions, drag, isActive, item, itemLabel, onClose, onWillOpen, row }: {
  actions: ComparisonPanelAction[];
  drag(): void;
  isActive: boolean;
  item: T;
  itemLabel: string;
  onClose(methods: SwipeableMethods): void;
  onWillOpen(methods: SwipeableMethods): void;
  row: ReactNode;
}) {
  const swipeableRef = useRef<SwipeableMethods>(null);
  const swipeDirection = useSharedValue(0);
  const adjacentActionColor = actions[0]?.backgroundColor ?? tokens.color.surfaceMuted;
  const [swipeSide, setSwipeSide] = useState<"neutral" | "right">("neutral");
  const renderRightActions = (progress: SharedValue<number>, _translation: SharedValue<number>, methods: SwipeableMethods) => (
    <DirectionalSwipeSurface direction={swipeDirection} progress={progress} side="right" style={[styles.actions, { width: actions.length * 48 }]}>
      {actions.map((action) => (
        <Pressable
          accessibilityLabel={action.label}
          accessibilityRole="button"
          key={action.label}
          onPress={() => { methods.close(); action.onPress(); }}
          style={({ pressed }) => [styles.action, { backgroundColor: action.backgroundColor }, pressed && styles.pressed]}>
          {action.icon}
        </Pressable>
      ))}
    </DirectionalSwipeSurface>
  );

  return (
    <ScaleDecorator activeScale={1.018}>
      <View style={styles.swipeUnderlay}>
      <View pointerEvents="none" style={[styles.swipeOvershoot, styles.swipeOvershootLeft]} />
      <View pointerEvents="none" style={[styles.swipeOvershoot, styles.swipeOvershootRight, { backgroundColor: swipeSide === "right" ? adjacentActionColor : tokens.color.surfaceMuted }]} />
      <ReanimatedSwipeable
        containerStyle={styles.swipeContainer}
        friction={2}
        onSwipeableClose={() => { swipeDirection.value = 0; setSwipeSide("neutral"); if (swipeableRef.current) onClose(swipeableRef.current); }}
        onSwipeableOpenStartDrag={(direction) => { swipeDirection.value = direction === SwipeDirection.RIGHT ? 1 : -1; if (direction === SwipeDirection.LEFT) setSwipeSide("right"); }}
        onSwipeableWillOpen={() => { if (swipeableRef.current) onWillOpen(swipeableRef.current); }}
        overshootFriction={8}
        overshootLeft
        overshootRight
        ref={swipeableRef}
        renderRightActions={renderRightActions}
        rightThreshold={36}>
        <Pressable
          accessibilityHint="Desliza hacia la izquierda para ver acciones. Mantén pulsado y arrastra para reordenar."
          accessibilityLabel={itemLabel}
          delayLongPress={320}
          disabled={isActive}
          onLongPress={() => beginComparisonPanelDrag(drag)}
          style={[styles.row, isActive && styles.rowActive]}>
          {row}
          {isActive ? <View pointerEvents="none" style={styles.rowBottomBorder} /> : null}
        </Pressable>
      </ReanimatedSwipeable>
      </View>
    </ScaleDecorator>
  );
}

export function ComparisonPanelGestureRows<T extends { id: string }>({ actions, itemLabel, items, onReorder, renderRow }: ComparisonPanelGestureRowsProps<T>) {
  const openSwipeableRef = useRef<SwipeableMethods | null>(null);
  const renderItem = ({ drag, getIndex, isActive, item }: RenderItemParams<T>) => (
    <GestureRow
      actions={actions(item)}
      drag={drag}
      isActive={isActive}
      item={item}
      itemLabel={itemLabel(item)}
      onClose={(methods) => { if (openSwipeableRef.current === methods) openSwipeableRef.current = null; }}
      onWillOpen={(methods) => {
        if (openSwipeableRef.current && openSwipeableRef.current !== methods) openSwipeableRef.current.close();
        openSwipeableRef.current = methods;
      }}
      row={renderRow(item, getIndex() ?? 0)}
    />
  );

  return (
    <NestableDraggableFlatList
      activationDistance={20}
      data={items}
      keyExtractor={(item) => item.id}
      onDragBegin={() => {
        openSwipeableRef.current?.close();
        openSwipeableRef.current = null;
      }}
      onDragEnd={({ data, from, to }) => { if (from !== to) void onReorder(data).catch(() => undefined); }}
      removeClippedSubviews={false}
      renderItem={renderItem}
      scrollEnabled={false}
    />
  );
}

export function StaticComparisonPanelRows<T extends { id: string }>({ items, renderRow }: Pick<ComparisonPanelGestureRowsProps<T>, "items" | "renderRow">) {
  return <>{items.map((item, index) => <Fragment key={item.id}>{renderRow(item, index)}</Fragment>)}</>;
}

const styles = StyleSheet.create({
  action: { alignItems: "center", alignSelf: "stretch", flex: 1, justifyContent: "center", width: 48 },
  actions: { alignSelf: "stretch", flexDirection: "row" },
  pressed: { opacity: 0.72 },
  row: { backgroundColor: tokens.color.surfaceMuted },
  rowActive: {
    backgroundColor: "#3a3a3a",
    borderTopColor: tokens.color.borderDefault,
    borderTopWidth: 1,
    elevation: 4,
    shadowColor: "#000000",
    shadowOffset: { height: 2, width: 0 },
    shadowOpacity: 0.14,
    shadowRadius: 5,
    zIndex: 10,
  },
  rowBottomBorder: { backgroundColor: tokens.color.borderDefault, bottom: 0, height: 1, left: 0, position: "absolute", right: 0 },
  swipeContainer: { backgroundColor: "transparent" },
  swipeUnderlay: { backgroundColor: tokens.color.surfaceMuted, position: "relative" },
  swipeOvershoot: { backgroundColor: tokens.color.surfaceMuted, bottom: 0, position: "absolute", top: 0, width: "50%" },
  swipeOvershootLeft: { left: 0 },
  swipeOvershootRight: { right: 0 },
});
