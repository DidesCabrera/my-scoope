import { Fragment, type ReactNode, useRef } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { NestableDraggableFlatList, ScaleDecorator, type RenderItemParams } from "react-native-draggable-flatlist";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import ReanimatedSwipeable, { type SwipeableMethods } from "react-native-gesture-handler/ReanimatedSwipeable";
import Animated from "react-native-reanimated";

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
  const longPressGesture = Gesture.LongPress().minDuration(320).onStart(drag).runOnJS(true);
  const renderRightActions = (_progress: unknown, _translation: unknown, methods: SwipeableMethods) => (
    <View style={[styles.actions, { width: actions.length * 48 }]}>
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
    <ScaleDecorator activeScale={1.018}>
      <ReanimatedSwipeable
        friction={2}
        onSwipeableClose={() => { if (swipeableRef.current) onClose(swipeableRef.current); }}
        onSwipeableWillOpen={() => { if (swipeableRef.current) onWillOpen(swipeableRef.current); }}
        overshootFriction={8}
        overshootRight={false}
        ref={swipeableRef}
        renderRightActions={renderRightActions}
        rightThreshold={36}>
        <GestureDetector gesture={longPressGesture}>
          <Animated.View
            accessibilityHint="Desliza hacia la izquierda para ver acciones. Mantén pulsado y arrastra para reordenar."
            accessibilityLabel={itemLabel}
            style={[styles.row, isActive && styles.rowActive]}>
            {row}
          </Animated.View>
        </GestureDetector>
      </ReanimatedSwipeable>
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
  rowActive: { opacity: 0.92 },
});
