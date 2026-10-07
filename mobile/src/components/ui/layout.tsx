import type { PropsWithChildren, ReactElement, ReactNode } from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useFocusEffect } from "expo-router";
import { type RefreshControlProps, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { tokens } from "@/design/tokens";

const BOTTOM_SPACING = 96;

type ScreenProps = PropsWithChildren<{
  contentStyle?: StyleProp<ViewStyle>;
  headerMode?: "automatic" | "preserve";
  onHeaderVisibilityChange?: (visible: boolean) => void;
  refreshControl?: ReactElement<RefreshControlProps>;
  scroll?: boolean | "auto";
  scrollHeader?: ReactNode;
  stickyHeader?: ReactNode;
  stickyHeaderStyle?: StyleProp<ViewStyle>;
}>;

const ScreenScrollContext = createContext<{ setPanelDragging(dragging: boolean): void }>({ setPanelDragging: () => undefined });

export function useScreenScrollControl() {
  return useContext(ScreenScrollContext);
}

export function Screen({ children, scroll = true, contentStyle, headerMode = "automatic", onHeaderVisibilityChange, refreshControl, scrollHeader, stickyHeader, stickyHeaderStyle }: ScreenProps) {
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [panelDragging, setPanelDragging] = useState(false);
  const [contentHeight, setContentHeight] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const scrollControl = useMemo(() => ({ setPanelDragging }), []);
  useFocusEffect(useCallback(() => {
    if (headerMode === "preserve") return undefined;
    setHeaderPresentation({ mode: "default", identityVisible: compactHeaderVisible });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, headerMode, setHeaderPresentation]));
  const content = <View style={[styles.screenContent, contentStyle]}>{children}</View>;
  const stickyHeaderIndex = stickyHeader ? (scrollHeader ? 1 : 0) : undefined;
  const setCompactIdentityVisible = useCallback((visible: boolean) => {
    setCompactHeaderVisible(visible);
    onHeaderVisibilityChange?.(visible);
  }, [onHeaderVisibilityChange]);
  const contentOverflows = contentHeight > viewportHeight + 1;
  const scrollEnabled = !panelDragging && (scroll === true || (scroll === "auto" && contentOverflows));
  return (
    <ScreenScrollContext.Provider value={scrollControl}>
    <SafeAreaView style={styles.safeArea} edges={["left", "right"]}>
      {scroll ? (
        <NestableScrollContainer
          alwaysBounceVertical={scroll === "auto" ? contentOverflows : undefined}
          bounces={scroll === "auto" ? contentOverflows : undefined}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={(_width, height) => setContentHeight(height)}
          onLayout={({ nativeEvent }) => setViewportHeight(nativeEvent.layout.height)}
          onScroll={(event) => setCompactIdentityVisible(isHeaderIdentityVisible(event.nativeEvent.contentOffset.y))}
          refreshControl={refreshControl}
          scrollEnabled={scrollEnabled}
          scrollEventThrottle={16}
          showsVerticalScrollIndicator={false}
          stickyHeaderIndices={stickyHeaderIndex === undefined ? undefined : [stickyHeaderIndex]}
        >
          {scrollHeader ? <View style={styles.scrollHeader}>{scrollHeader}</View> : null}
          {stickyHeader ? <View style={[styles.stickyHeader, stickyHeaderStyle]}>{stickyHeader}</View> : null}
          {content}
        </NestableScrollContainer>
      ) : content}
    </SafeAreaView>
    </ScreenScrollContext.Provider>
  );
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <View style={styles.brandRow}>
      <View style={styles.brandMark}>
        <Text style={styles.brandMarkText}>M</Text>
      </View>
      <View>
        <Text style={[styles.brandName, compact && styles.brandNameCompact]}>MY SCOOPE</Text>
        {!compact && <Text style={styles.brandCaption}>Tu programa. Hoy.</Text>}
      </View>
    </View>
  );
}

export function AppHeader({ eyebrow, eyebrowIcon, title, action, alignment = "bottom" }: { alignment?: "bottom" | "center"; eyebrow?: string; eyebrowIcon?: ReactNode; title: string; action?: ReactNode }) {
  return (
    <View style={[styles.header, alignment === "center" && styles.headerCentered]}>
      <View style={styles.headerCopy}>
        {eyebrow ? <View style={styles.eyebrowRow}>{eyebrowIcon}<Text style={styles.eyebrow}>{eyebrow}</Text></View> : null}
        <Text style={styles.title}>{title}</Text>
      </View>
      {action}
    </View>
  );
}

export const layoutStyles = StyleSheet.create({
  cardContentBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
});

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: tokens.color.surfaceApp },
  scrollContent: { flexGrow: 1 },
  screenContent: { flexGrow: 1, gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, paddingBottom: BOTTOM_SPACING },
  scrollHeader: { paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  stickyHeader: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.md, paddingBottom: tokens.spacing.md, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, zIndex: 2 },
  brandRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  brandMark: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  brandMarkText: { color: tokens.color.surfaceApp, fontSize: 20, fontWeight: "900" },
  brandName: { color: tokens.color.textMain, fontSize: 15, fontWeight: "900", letterSpacing: 1.8 },
  brandNameCompact: { fontSize: 13 },
  brandCaption: { color: tokens.color.textSoft, fontSize: 12, marginTop: 2 },
  header: { alignItems: "flex-end", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  headerCentered: { alignItems: "center" },
  headerCopy: { flex: 1, gap: tokens.spacing.xs },
  eyebrowRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: "800", letterSpacing: -0.5 },
});
