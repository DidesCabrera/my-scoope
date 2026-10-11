import { Search, X } from "lucide-react-native";
import { ActivityIndicator, Pressable, StyleSheet, TextInput, type TextInputProps, View } from "react-native";

import { tokens } from "@/design/tokens";
import { layoutStyles } from "./layout";

type SearchFieldProps = Pick<TextInputProps, "accessibilityLabel" | "autoCapitalize" | "autoCorrect" | "onSubmitEditing" | "placeholder" | "returnKeyType"> & {
  bleed?: boolean;
  busy?: boolean;
  onChangeText(value: string): void;
  onClear?(): void;
  value: string;
};

export function SearchField({ bleed = false, busy = false, onChangeText, onClear, value, ...inputProps }: SearchFieldProps) {
  return (
    <View style={[styles.field, bleed && layoutStyles.cardContentBleed]}>
      <Search color={tokens.color.textSoft} size={20} />
      <TextInput
        {...inputProps}
        onChangeText={onChangeText}
        placeholderTextColor={tokens.color.textSubtle}
        style={styles.input}
        value={value}
      />
      {busy ? <ActivityIndicator color={tokens.color.interactivePrimary} size="small" /> : null}
      {!busy && value && onClear ? (
        <Pressable accessibilityLabel="Limpiar búsqueda" hitSlop={6} onPress={onClear} style={styles.clearButton}>
          <X color={tokens.color.textMuted} size={18} />
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  clearButton: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  field: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  input: { color: tokens.color.textMain, flex: 1, fontSize: 16, minHeight: 36, paddingVertical: 0 },
});
