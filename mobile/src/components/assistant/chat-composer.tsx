import { ArrowUp } from "lucide-react-native";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";

export function ChatComposer({ disabled, loading, maxLength, onChangeText, onSend, supportingText, value }: {
  disabled: boolean;
  loading: boolean;
  maxLength: number;
  onChangeText(value: string): void;
  onSend(): void;
  supportingText?: string;
  value: string;
}) {
  const remaining = Math.max(maxLength - value.length, 0);
  const sendDisabled = disabled || loading || !value.trim();
  return (
    <SafeAreaView edges={["bottom"]} style={styles.container}>
      <View style={styles.composer}>
        <TextInput
          accessibilityLabel="Mensaje para el Asistente"
          blurOnSubmit={false}
          editable={!disabled && !loading}
          maxLength={maxLength}
          multiline
          onChangeText={onChangeText}
          placeholder="Pregunta lo que quieras"
          placeholderTextColor={tokens.color.textSubtle}
          returnKeyType="default"
          selectionColor={tokens.color.interactivePrimary}
          style={styles.input}
          textAlignVertical="top"
          value={value}
        />
        <Pressable
          accessibilityLabel="Enviar"
          accessibilityRole="button"
          accessibilityState={{ disabled: sendDisabled }}
          disabled={sendDisabled}
          hitSlop={6}
          onPress={onSend}
          style={({ pressed }) => [styles.sendButton, sendDisabled && styles.sendButtonDisabled, pressed && styles.sendButtonPressed]}>
          {loading ? <ActivityIndicator color={tokens.color.textMain} size="small" /> : <ArrowUp color={sendDisabled ? tokens.color.textSubtle : tokens.color.surfaceApp} size={20} strokeWidth={3} />}
        </Pressable>
      </View>
      {supportingText || remaining <= 200 ? <View style={styles.meta}>{supportingText ? <Text style={styles.supportingText}>{supportingText}</Text> : null}{remaining <= 200 ? <Text style={styles.counter}>{remaining} caracteres</Text> : null}</View> : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  composer: { alignItems: "flex-end", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52, paddingBottom: 6, paddingLeft: tokens.spacing.lg, paddingRight: 6, paddingTop: 6 },
  container: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.compact, paddingBottom: tokens.spacing.md, paddingHorizontal: tokens.spacing.md, paddingTop: tokens.spacing.sm },
  counter: { color: tokens.color.textSubtle, fontSize: tokens.type.label },
  input: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, lineHeight: 23, maxHeight: 120, minHeight: 38, paddingBottom: 8, paddingHorizontal: 0, paddingTop: 8 },
  meta: { flexDirection: "row", justifyContent: "space-between", paddingHorizontal: tokens.spacing.sm },
  sendButton: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.pill, height: 38, justifyContent: "center", width: 38 },
  sendButtonDisabled: { backgroundColor: tokens.color.surfaceElevated },
  sendButtonPressed: { opacity: 0.72, transform: [{ scale: 0.96 }] },
  supportingText: { color: tokens.color.textSubtle, flex: 1, fontSize: tokens.type.label },
});
