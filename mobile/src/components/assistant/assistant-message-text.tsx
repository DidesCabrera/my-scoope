import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

import { parseAssistantText } from "./assistant-message-parser";

const INLINE_MARKUP = /(\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\*[^*\n]+\*|_[^_\n]+_)/g;

function inlineText(source: string): ReactNode[] {
  return source.split(INLINE_MARKUP).filter(Boolean).map((part, index) => {
    const key = `${index}-${part}`;
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
      return <Text key={key} style={styles.strong}>{part.slice(2, -2)}</Text>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <Text key={key} style={styles.code}>{part.slice(1, -1)}</Text>;
    }
    if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
      return <Text key={key} style={styles.emphasis}>{part.slice(1, -1)}</Text>;
    }
    return part;
  });
}

export function AssistantMessageText({ children }: { children: string }) {
  return (
    <View accessibilityLabel={children} style={styles.content}>
      {parseAssistantText(children).map((block, index) => {
        const key = `${block.kind}-${index}`;
        if (block.kind === "heading") {
          return <Text key={key} selectable style={[styles.text, styles.heading, block.level > 1 && styles.subheading]}>{inlineText(block.text)}</Text>;
        }
        if (block.kind === "unordered-item" || block.kind === "ordered-item") {
          return <View key={key} style={styles.listRow}><Text style={styles.marker}>{block.kind === "ordered-item" ? `${block.number}.` : "•"}</Text><Text selectable style={[styles.text, styles.listText]}>{inlineText(block.text)}</Text></View>;
        }
        if (block.kind === "quote") {
          return <View key={key} style={styles.quote}><Text selectable style={[styles.text, styles.quoteText]}>{inlineText(block.text)}</Text></View>;
        }
        return <Text key={key} selectable style={styles.text}>{inlineText(block.text)}</Text>;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  code: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.sm, fontFamily: "Courier", fontSize: tokens.type.caption, paddingHorizontal: 4 },
  content: { gap: tokens.spacing.md },
  emphasis: { fontStyle: "italic" },
  heading: { fontSize: tokens.type.section, fontWeight: "800", lineHeight: 27 },
  listRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.sm, paddingLeft: tokens.spacing.xs },
  listText: { flex: 1 },
  marker: { color: tokens.color.assistantMessageForeground, fontSize: tokens.type.body, fontWeight: "800", lineHeight: 25, minWidth: 20, textAlign: "right" },
  quote: { borderLeftColor: tokens.color.borderDefault, borderLeftWidth: 3, paddingLeft: tokens.spacing.md },
  quoteText: { color: tokens.color.assistantMessageForeground },
  strong: { fontWeight: "800" },
  subheading: { fontSize: tokens.type.body, lineHeight: 25 },
  text: { color: tokens.color.assistantMessageForeground, fontSize: tokens.type.body, lineHeight: 25 },
});
