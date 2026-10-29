import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text } from "react-native";

import { tokens } from "@/design/tokens";

type PickerCardActionProps = {
  icon?: ReactNode;
  label: string;
  onPress(): void;
  subject: string;
  variant?: "cardFullWidth" | "default" | "mutedFullWidth";
};

export function PickerCardAction({ icon, label, onPress, subject, variant = "default" }: PickerCardActionProps) {
  return (
    <Pressable
      accessibilityLabel={`${label}: ${subject}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.action,
        variant === "mutedFullWidth" && styles.actionMutedFullWidth,
        variant === "cardFullWidth" && styles.actionCardFullWidth,
        pressed && styles.pressed,
      ]}>
      {icon}
      <Text style={[styles.label, variant !== "default" && styles.labelMutedFullWidth]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  action: {
    alignItems: "center",
    backgroundColor: tokens.color.textMain,
    borderRadius: tokens.radius.pill,
    flexDirection: "row",
    gap: tokens.spacing.sm,
    justifyContent: "center",
    minHeight: 38,
    minWidth: 112,
    paddingHorizontal: tokens.spacing.lg,
  },
  actionMutedFullWidth: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceMuted, minHeight: 38, width: "100%" },
  actionCardFullWidth: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceCard, minHeight: 38, width: "100%" },
  label: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: "800" },
  labelMutedFullWidth: { color: tokens.color.textMain },
  pressed: { opacity: 0.68 },
});
