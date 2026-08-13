import { StyleSheet, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export function ChatComposer({ disabled, loading, maxLength, onChangeText, onSend, value }: {
  disabled: boolean;
  loading: boolean;
  maxLength: number;
  onChangeText(value: string): void;
  onSend(): void;
  value: string;
}) {
  const remaining = Math.max(maxLength - value.length, 0);
  return (
    <View style={styles.container}>
      <TextInput
        accessibilityLabel="Mensaje para el Asistente"
        editable={!disabled && !loading}
        maxLength={maxLength}
        multiline
        blurOnSubmit={false}
        onChangeText={onChangeText}
        placeholder="Escribe tu mensaje…"
        placeholderTextColor={tokens.color.textSubtle}
        selectionColor={tokens.color.interactivePrimary}
        style={styles.input}
        textAlignVertical="top"
        returnKeyType="default"
        value={value}
      />
      <View style={styles.footer}>
        <Text style={styles.counter}>{remaining} caracteres</Text>
        <View style={styles.action}><Button disabled={disabled || !value.trim()} label="Enviar" loading={loading} onPress={onSend} /></View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  action: { minWidth: 120 },
  container: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.md },
  counter: { color: tokens.color.textSoft, flex: 1, fontSize: tokens.type.label },
  footer: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  input: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24, minHeight: 110, padding: 0 },
});
