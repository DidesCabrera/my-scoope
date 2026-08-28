import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text } from "react-native";

import { tokens } from "@/design/tokens";

type Props = {
  accessibilityLabel: string;
  bleed?: boolean;
  label: string;
  onPress(): void;
};

export function DetailLinkRow({ accessibilityLabel, bleed = true, label, onPress }: Props) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="link"
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [styles.root, bleed && styles.bleed, pressed && styles.rootPressed]}
    >
      <Text style={styles.label}>{label}</Text>
      <ChevronRight color={tokens.color.textMain} size={22} strokeWidth={2.2} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  label: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  root: { alignItems: "center", alignSelf: "flex-end", borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.xs, justifyContent: "center", minHeight: 40, paddingHorizontal: tokens.spacing.xs },
  rootPressed: { backgroundColor: tokens.color.borderSoft, opacity: 0.72 },
});
