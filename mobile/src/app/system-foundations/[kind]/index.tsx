import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LearningArticle, LearningCatalogData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { LearningIcon, learningStyles } from "@/components/learning/learning-ui";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Card, EntityCardAction, EntityCardActions, InlineNotice, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function LearningCatalogScreen() {
  const { kind: rawKind } = useLocalSearchParams<{ kind?: string }>();
  const kind = rawKind === "manuals" ? "manuals" : "nutrition";
  const title = kind === "nutrition" ? "Fundamentos Nutricionales" : "Manuales de uso";
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [articles, setArticles] = useState<LearningArticle[]>([]);
  const [error, setError] = useState<string | null>(null);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/system-foundations", mode: "back", title });
    if (status === "authenticated") void apiRequest<LearningCatalogData>("/api/v1/learning").then((data) => setArticles(data[kind])).catch((next) => setError(userFacingError(next)));
    return () => setHeaderPresentation({ mode: "default" });
  }, [apiRequest, kind, setHeaderPresentation, status, title]));
  if (status === "anonymous") return <Redirect href="/login" />;
  return <Screen headerMode="preserve">
    <AppHeader eyebrow="Biblioteca de aprendizaje" title={title} />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {articles.map((article) => <Card key={article.slug} style={learningStyles.card}>
      <View style={learningStyles.cardHeading}><View style={learningStyles.cardText}><Text style={learningStyles.title}>{article.title}</Text><Text style={learningStyles.summary}>{article.summary}</Text></View><LearningIcon name={article.icon} /></View>
      <EntityCardActions><EntityCardAction label={`Leer ${article.title}`} onPress={() => router.push(`/system-foundations/${kind}/${article.slug}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} /></EntityCardAction></EntityCardActions>
    </Card>)}
  </Screen>;
}
