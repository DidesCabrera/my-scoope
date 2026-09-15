import { Fragment, type ReactNode, useRef, useState } from "react";
import { type LayoutChangeEvent, Pressable, StyleSheet, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import ReanimatedSwipeable, { type SwipeableMethods } from "react-native-gesture-handler/ReanimatedSwipeable";
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withSpring, withTiming } from "react-native-reanimated";

import { tokens } from "@/design/tokens";
import { type ComparisonRowLayout, reorderedItemsForDrop } from "./comparison-panel-reorder";

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

function GestureRow<T extends { id: string }>({ actions, index, item, itemLabel, onClose, onDragFinish, onDragStart, onDrop, onMove, onWillOpen, row }: {
  actions: ComparisonPanelAction[];
  index: number;
  item: T;
  itemLabel: string;
  onClose(methods: SwipeableMethods): void;
  onDragFinish(): void;
  onDragStart(): void;
  onDrop(index: number, translationY: number): void;
  onMove(index: number, offset: number): void;
  onWillOpen(methods: SwipeableMethods): void;
  row: ReactNode;
}) {
  const swipeableRef = useRef<SwipeableMethods>(null);
  const dragging = useSharedValue(0);
  const translationY = useSharedValue(0);
  const dragGesture = Gesture.Pan()
    .activateAfterLongPress(320)
    .onStart(() => {
      dragging.value = 1;
      runOnJS(onDragStart)();
    })
    .onUpdate((event) => { translationY.value = event.translationY; })
    .onEnd((event) => { runOnJS(onDrop)(index, event.translationY); })
    .onFinalize(() => {
      dragging.value = 0;
      translationY.value = withSpring(0, { damping: 20, stiffness: 260 });
      runOnJS(onDragFinish)();
    });
  const animatedRowStyle = useAnimatedStyle(() => ({
    opacity: withTiming(dragging.value ? 0.94 : 1, { duration: 100 }),
    transform: [
      { translateY: translationY.value },
      { scale: withTiming(dragging.value ? 1.018 : 1, { duration: 100 }) },
    ],
  }));
  const renderRightActions = (_progress: unknown, _translation: unknown, methods: SwipeableMethods) => (
    <View style={styles.actions}>
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
    </View>
  );

  return (
    <ReanimatedSwipeable
      friction={2}
      onSwipeableClose={() => { if (swipeableRef.current) onClose(swipeableRef.current); }}
      onSwipeableWillOpen={() => { if (swipeableRef.current) onWillOpen(swipeableRef.current); }}
      overshootFriction={8}
      overshootRight={false}
      ref={swipeableRef}
      renderRightActions={renderRightActions}
      rightThreshold={36}>
      <GestureDetector gesture={dragGesture}>
        <Animated.View
          accessibilityActions={[
            ...(index > 0 ? [{ label: `Mover ${itemLabel} hacia arriba`, name: "move-up" }] : []),
            { label: `Mover ${itemLabel} hacia abajo`, name: "move-down" },
          ]}
          accessibilityHint="Desliza hacia la izquierda para ver acciones. Mantén pulsado y arrastra para reordenar."
          accessibilityLabel={itemLabel}
          onAccessibilityAction={(event) => {
            if (event.nativeEvent.actionName === "move-up") onMove(index, -1);
            if (event.nativeEvent.actionName === "move-down") onMove(index, 1);
          }}
          style={[styles.row, animatedRowStyle]}>
          {row}
        </Animated.View>
      </GestureDetector>
    </ReanimatedSwipeable>
  );
}

export function ComparisonPanelGestureRows<T extends { id: string }>({ actions, itemLabel, items, onReorder, renderRow }: ComparisonPanelGestureRowsProps<T>) {
  const openSwipeableRef = useRef<SwipeableMethods | null>(null);
  const rowLayoutsRef = useRef<Record<string, ComparisonRowLayout>>({});
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const closeOpenSwipeable = () => {
    openSwipeableRef.current?.close();
    openSwipeableRef.current = null;
  };
  const persistReorder = (nextItems: T[]) => {
    if (nextItems !== items) void onReorder(nextItems).catch(() => undefined);
  };
  const moveByOffset = (sourceIndex: number, offset: number) => {
    const destinationIndex = sourceIndex + offset;
    if (destinationIndex < 0 || destinationIndex >= items.length) return;
    const reordered = [...items];
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(destinationIndex, 0, moved);
    persistReorder(reordered);
  };
  const recordLayout = (id: string, event: LayoutChangeEvent) => {
    const { height, y } = event.nativeEvent.layout;
    rowLayoutsRef.current[id] = { height, y };
  };

  return (
    <View>
      {items.map((item, index) => (
        <View key={item.id} onLayout={(event) => recordLayout(item.id, event)} style={draggingId === item.id && styles.rowContainerActive}>
          <GestureRow
            actions={actions(item)}
            index={index}
            item={item}
            itemLabel={itemLabel(item)}
            onClose={(methods) => { if (openSwipeableRef.current === methods) openSwipeableRef.current = null; }}
            onDragFinish={() => setDraggingId(null)}
            onDragStart={() => { closeOpenSwipeable(); setDraggingId(item.id); }}
            onDrop={(sourceIndex, translation) => persistReorder(reorderedItemsForDrop(items, rowLayoutsRef.current, sourceIndex, translation))}
            onMove={moveByOffset}
            onWillOpen={(methods) => {
              if (openSwipeableRef.current && openSwipeableRef.current !== methods) openSwipeableRef.current.close();
              openSwipeableRef.current = methods;
            }}
            row={renderRow(item, index)}
          />
        </View>
      ))}
    </View>
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
  rowContainerActive: { elevation: 6, zIndex: 2 },
});
