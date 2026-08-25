import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

type Props = {
  accessibilityLabel: string;
  bleed?: boolean;
  label: string;
  onPress(): void;
};

export function DetailLinkRow({ accessibilityLabel, bleed = true, label, onPress }: Props) {
  return (
    <View style={[styles.root, bleed && styles.bleed]}>
      <Text style={styles.label}>{label}</Text>
      <Pressable
        accessibilityLabel={accessibilityLabel}
        accessibilityRole="link"
        hitSlop={8}
        onPress={onPress}
        style={({ pressed }) => [styles.action, pressed && styles.actionPressed]}
      >
        <ChevronRight color={tokens.color.textMain} size={22} strokeWidth={2.2} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  action: { alignItems: "center", borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  actionPressed: { backgroundColor: tokens.color.borderSoft, opacity: 0.72 },
  bleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  label: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  root: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 48, paddingLeft: tokens.spacing.md, paddingRight: tokens.spacing.xs },
});
