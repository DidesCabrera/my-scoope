import type { PropsWithChildren, ReactNode } from "react";
import {
  ActivityIndicator,
  KeyboardTypeOptions,
  Pressable,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  View,
  ViewStyle,
} from "react-native";

import { tokens } from "@/design/tokens";
import { Screen } from "./layout";

export { Screen };

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

export function AppHeader({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <View style={styles.header}>
      <View style={styles.headerCopy}>
        {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
        <Text style={styles.title}>{title}</Text>
      </View>
      {action}
    </View>
  );
}

export function Card({
  children,
  accent,
  muted = false,
  style,
}: PropsWithChildren<{ accent?: string; muted?: boolean; style?: StyleProp<ViewStyle> }>) {
  return (
    <View style={[styles.card, muted && styles.cardMuted, accent ? { borderTopColor: accent, borderTopWidth: 3 } : null, style]}>
      {children}
    </View>
  );
}

export function SectionTitle({ title, detail }: { title: string; detail?: string }) {
  return (
    <View style={styles.sectionTitleRow}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {detail ? <Text style={styles.sectionDetail}>{detail}</Text> : null}
    </View>
  );
}

export function Pill({ label, color = tokens.color.interactivePrimary }: { label: string; color?: string }) {
  return (
    <View style={[styles.pill, { borderColor: color }]}>
      <Text style={[styles.pillText, { color }]}>{label}</Text>
    </View>
  );
}

export function Button({
  bleed = false,
  label,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
}: {
  bleed?: boolean;
  label: string;
  onPress(): void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  loading?: boolean;
}) {
  const buttonStyle = variant === "primary" ? styles.buttonPrimary : styles.buttonSecondary;
  const textStyle = variant === "primary" ? styles.buttonPrimaryText : styles.buttonSecondaryText;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        bleed && styles.buttonBleed,
        buttonStyle,
        variant === "danger" && styles.buttonDanger,
        (disabled || loading) && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}>
      {loading ? <ActivityIndicator color={variant === "primary" ? tokens.color.surfaceApp : tokens.color.textMain} /> : null}
      <Text style={[textStyle, variant === "danger" && styles.buttonDangerText]}>{label}</Text>
    </Pressable>
  );
}

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize = "none",
  secureTextEntry = false,
  multiline = false,
}: {
  label: string;
  value: string;
  onChangeText(value: string): void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  secureTextEntry?: boolean;
  multiline?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        autoCapitalize={autoCapitalize}
        keyboardType={keyboardType}
        multiline={multiline}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={tokens.color.textSubtle}
        selectionColor={tokens.color.interactivePrimary}
        secureTextEntry={secureTextEntry}
        style={[styles.input, multiline && styles.inputMultiline]}
        value={value}
      />
    </View>
  );
}

export function ChoiceRow<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange(value: T): void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.choiceRow}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              onPress={() => onChange(option.value)}
              style={[styles.choice, selected && styles.choiceSelected]}>
              <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export function InlineNotice({ children, tone = "info" }: PropsWithChildren<{ tone?: "info" | "warning" | "error" }>) {
  const color = tone === "error" ? tokens.color.danger : tone === "warning" ? tokens.color.warning : tokens.color.interactivePrimary;
  return (
    <View style={[styles.notice, { borderLeftColor: color }]}>
      <Text style={styles.noticeText}>{children}</Text>
    </View>
  );
}

export function ProgressBar({ value }: { value: number }) {
  const normalized = Math.max(0, Math.min(value, 100));
  return (
    <View style={styles.progressTrack} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: normalized }}>
      <View style={[styles.progressFill, { width: `${normalized}%` }]} />
    </View>
  );
}

export function LoadingState({ label = "Preparando tu día…" }: { label?: string }) {
  return (
    <Screen scroll={false} contentStyle={styles.loadingState} headerMode="preserve">
      <Brand />
      <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
      <Text style={styles.mutedText}>{label}</Text>
    </Screen>
  );
}

export const textStyles = StyleSheet.create({
  body: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24 },
  muted: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  caption: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  strong: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
});

const styles = StyleSheet.create({
  brandRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  brandMark: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  brandMarkText: { color: tokens.color.surfaceApp, fontSize: 20, fontWeight: "900" },
  brandName: { color: tokens.color.textMain, fontSize: 15, fontWeight: "900", letterSpacing: 1.8 },
  brandNameCompact: { fontSize: 13 },
  brandCaption: { color: tokens.color.textSoft, fontSize: 12, marginTop: 2 },
  header: { alignItems: "flex-end", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  headerCopy: { flex: 1, gap: 4 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "700", letterSpacing: 1.2, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: "800", letterSpacing: -0.5 },
  card: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.card.gap, padding: tokens.card.outerPadding },
  cardMuted: { backgroundColor: tokens.color.surfaceMuted },
  sectionTitleRow: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  sectionTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  sectionDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
  pill: { alignSelf: "flex-start", borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 5 },
  pillText: { fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 0.4 },
  button: { alignItems: "center", borderRadius: tokens.radius.lg, flexDirection: "row", gap: 8, justifyContent: "center", minHeight: 54, paddingHorizontal: tokens.spacing.lg },
  buttonBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  buttonPrimary: { backgroundColor: tokens.color.textMain },
  buttonSecondary: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderWidth: 1 },
  buttonDanger: { backgroundColor: "transparent", borderColor: tokens.color.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.72, transform: [{ translateY: 1 }] },
  buttonPrimaryText: { color: tokens.color.surfaceApp, fontSize: 16, fontWeight: "800" },
  buttonSecondaryText: { color: tokens.color.textMain, fontSize: 16, fontWeight: "700" },
  buttonDangerText: { color: tokens.color.danger },
  field: { gap: 7 },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  input: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, color: tokens.color.textMain, fontSize: 17, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: 16 },
  inputMultiline: { minHeight: 104, paddingTop: 15, textAlignVertical: "top" },
  choiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  choice: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 50, paddingHorizontal: 10 },
  choiceSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  choiceText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: "700" },
  choiceTextSelected: { color: tokens.color.surfaceApp },
  notice: { backgroundColor: tokens.color.surfaceMuted, borderLeftWidth: 3, borderRadius: tokens.radius.md, padding: tokens.spacing.md },
  noticeText: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 8, overflow: "hidden" },
  progressFill: { backgroundColor: tokens.color.program, borderRadius: tokens.radius.pill, height: "100%" },
  loadingState: { alignItems: "center", justifyContent: "center" },
  mutedText: { color: tokens.color.textMuted, fontSize: 15 },
});
