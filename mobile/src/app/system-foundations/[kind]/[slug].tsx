import { Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import * as Linking from "expo-linking";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LearningArticle, LearningCatalogData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { LearningIcon, learningStyles } from "@/components/learning/learning-ui";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Button, Card, InlineNotice, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function LearningArticleScreen() {
  const params = useLocalSearchParams<{ kind?: string; slug?: string }>();
  const kind = params.kind === "manuals" ? "manuals" : "nutrition";
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [article, setArticle] = useState<LearningArticle | null>(null);
  const [error, setError] = useState<string | null>(null);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/system-foundations/${kind}`, mode: "back", title: article?.title ?? "Detalle" });
    if (status === "authenticated") void apiRequest<LearningCatalogData>("/api/v1/learning").then((data) => setArticle(data[kind].find((item) => item.slug === params.slug) ?? null)).catch((next) => setError(userFacingError(next)));
    return () => setHeaderPresentation({ mode: "default" });
  }, [apiRequest, article?.title, kind, params.slug, setHeaderPresentation, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  return <Screen headerMode="preserve">
    <AppHeader eyebrow={kind === "nutrition" ? "Fundamento nutricional" : "Manual de uso"} title={article?.title ?? "Detalle"} />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {article ? <>
      <Card style={learningStyles.card}><View style={learningStyles.cardHeading}><LearningIcon name={article.icon} /><Text style={learningStyles.summary}>{article.summary}</Text></View></Card>
      {article.sections.map((section) => <Card key={section.heading} style={styles.section}><Text style={learningStyles.title}>{section.heading}</Text><Text style={styles.body}>{section.body}</Text></Card>)}
      <InlineNotice tone="info"><Text style={styles.takeaway}>Idea principal: {article.takeaway}</Text></InlineNotice>
      {kind === "nutrition" ? <Text style={styles.disclaimer}>Contenido educativo general. No sustituye evaluación, diagnóstico ni indicaciones de un profesional de salud.</Text> : null}
      {article.source_url ? <Button label={`Fuente: ${article.source_label}`} onPress={() => void Linking.openURL(article.source_url)} variant="secondary" /> : null}
    </> : null}
  </Screen>;
}

const styles = StyleSheet.create({ body: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 }, disclaimer: { color: tokens.color.textSoft, fontSize: tokens.type.label, lineHeight: 17 }, section: { gap: tokens.spacing.sm }, takeaway: { color: tokens.color.textMain, lineHeight: 20 } });
