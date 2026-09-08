import type { PropsWithChildren, ReactNode } from "react";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { NativeScrollEvent, NativeSyntheticEvent, ScrollView, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

type ScreenProps = PropsWithChildren<{
  contentStyle?: StyleProp<ViewStyle>;
  headerMode?: "automatic" | "preserve";
  onScroll?: (event: NativeSyntheticEvent<NativeScrollEvent>) => void;
  scroll?: boolean;
  scrollHeader?: ReactNode;
  stickyHeader?: ReactNode;
}>;

export function Screen({ children, scroll = true, contentStyle, headerMode = "automatic", onScroll, scrollHeader, stickyHeader }: ScreenProps) {
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  useFocusEffect(useCallback(() => {
    if (headerMode === "preserve") return undefined;
    setHeaderPresentation({ mode: "default", identityVisible: compactHeaderVisible });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, headerMode, setHeaderPresentation]));
  const content = <View style={[styles.screenContent, contentStyle]}>{children}</View>;
  const stickyHeaderIndex = stickyHeader ? (scrollHeader ? 1 : 0) : undefined;
  return (
    <SafeAreaView style={styles.safeArea} edges={["left", "right"]}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          onScroll={(event) => { const visible = event.nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); onScroll?.(event); }}
          scrollEventThrottle={16}
          stickyHeaderIndices={stickyHeaderIndex === undefined ? undefined : [stickyHeaderIndex]}
        >
          {scrollHeader ? <View style={styles.scrollHeader}>{scrollHeader}</View> : null}
          {stickyHeader ? <View style={styles.stickyHeader}>{stickyHeader}</View> : null}
          {content}
        </ScrollView>
      ) : content}
    </SafeAreaView>
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

export function AppHeader({ eyebrow, title, action, alignment = "bottom" }: { alignment?: "bottom" | "center"; eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <View style={[styles.header, alignment === "center" && styles.headerCentered]}>
      <View style={styles.headerCopy}>
        {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
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
  screenContent: { flex: 1, gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, paddingBottom: 42 },
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
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "700", letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: "800", letterSpacing: -0.5 },
});
