import type { ReactNode } from "react";
import { ActivityIndicator, KeyboardTypeOptions, Pressable, StyleProp, StyleSheet, Switch, Text, TextInput, TextStyle, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

export function Button({
  bleed = true,
  icon,
  label,
  onPress,
  variant = "primary",
  multicolorSurface = "muted",
  disabled = false,
  loading = false,
}: {
  bleed?: boolean;
  icon?: ReactNode;
  label: string;
  onPress(): void;
  variant?: "primary" | "secondary" | "danger" | "multicolor";
  multicolorSurface?: "app" | "muted";
  disabled?: boolean;
  loading?: boolean;
}) {
  const multicolor = variant === "multicolor";
  const buttonStyle = variant === "primary" ? styles.buttonPrimary : multicolor ? styles.buttonMulticolor : styles.buttonSecondary;
  const textStyle = variant === "primary" ? styles.buttonPrimaryText : styles.buttonSecondaryText;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
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
      {multicolor ? <>
        <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
          <Defs>
            <LinearGradient id="button-border-macros" x1="0" x2="1" y1="0" y2="1">
              <Stop offset="0" stopColor={tokens.color.protein} />
              <Stop offset="0.5" stopColor={tokens.color.carbs} />
              <Stop offset="1" stopColor={tokens.color.fat} />
            </LinearGradient>
          </Defs>
          <Rect fill="url(#button-border-macros)" height="100%" width="100%" />
        </Svg>
        <View style={[styles.buttonMulticolorInset, multicolorSurface === "app" && styles.buttonMulticolorInsetApp]} />
      </> : null}
      {loading ? <ActivityIndicator color={variant === "primary" ? tokens.color.surfaceApp : tokens.color.textMain} /> : null}
      {!loading ? icon : null}
      <Text style={[textStyle, variant === "danger" && styles.buttonDangerText]}>{label}</Text>
    </Pressable>
  );
}

export function Field({
  hideLabel = false,
  inputStyle,
  label,
  labelIcon,
  labelStyle,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize = "none",
  autoCorrect,
  secureTextEntry = false,
}: {
  hideLabel?: boolean;
  inputStyle?: StyleProp<TextStyle>;
  label: string;
  labelIcon?: ReactNode;
  labelStyle?: StyleProp<TextStyle>;
  value: string;
  onChangeText(value: string): void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  autoCorrect?: boolean;
  secureTextEntry?: boolean;
}) {
  return (
    <View style={styles.field}>
      {!hideLabel ? <View style={styles.fieldLabelRow}>
        {labelIcon}
        <Text style={[styles.fieldLabel, labelStyle]}>{label}</Text>
      </View> : null}
      <TextInput
        accessibilityLabel={label}
        autoCapitalize={autoCapitalize}
        autoCorrect={autoCorrect}
        keyboardType={keyboardType}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={tokens.color.textSubtle}
        selectionColor={tokens.color.interactivePrimary}
        secureTextEntry={secureTextEntry}
        style={[styles.input, inputStyle]}
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
    <View style={styles.field} accessibilityRole="radiogroup">
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

export function SystemSwitch({ accessibilityLabel, disabled = false, onValueChange, value }: { accessibilityLabel: string; disabled?: boolean; onValueChange(value: boolean): void; value: boolean }) {
  return <Switch accessibilityLabel={accessibilityLabel} disabled={disabled} onValueChange={onValueChange} value={value} />;
}

const styles = StyleSheet.create({
  button: { alignItems: "center", borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 48, paddingHorizontal: tokens.spacing.lg },
  buttonBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  buttonPrimary: { backgroundColor: tokens.color.textMain },
  buttonMulticolor: { overflow: "hidden" },
  buttonMulticolorInset: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg - 2, bottom: 2, left: 2, position: "absolute", right: 2, top: 2 },
  buttonMulticolorInsetApp: { backgroundColor: tokens.color.surfaceApp },
  buttonSecondary: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderWidth: 1 },
  buttonDanger: { backgroundColor: "transparent", borderColor: tokens.color.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.72, transform: [{ translateY: 1 }] },
  buttonPrimaryText: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: "800" },
  buttonSecondaryText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
  buttonDangerText: { color: tokens.color.danger },
  field: { gap: 7 },
  fieldLabelRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  input: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, color: tokens.color.textMain, fontSize: 17, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  choiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  choice: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 50, paddingHorizontal: 10 },
  choiceSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  choiceText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: "700" },
  choiceTextSelected: { color: tokens.color.surfaceApp },
});
