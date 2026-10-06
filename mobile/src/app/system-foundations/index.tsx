import { type Href, Redirect, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { Text, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { AppHeader, Card, EntityCardAction, EntityCardActions, Screen } from "@/components/ui";
import { LearningIcon, learningStyles } from "@/components/learning/learning-ui";
import { tokens } from "@/design/tokens";

export default function SystemFoundationsScreen() {
  const router = useRouter();
  const { status } = useSession();
  if (status === "anonymous") return <Redirect href="/login" />;
  return <Screen>
    <AppHeader eyebrow="Aprender en My Scoope" title="Fundamentos Sistema" />
    <Text style={learningStyles.intro}>Comprende los conceptos nutricionales esenciales y aprende a usar las herramientas principales del sistema.</Text>
    <Card style={learningStyles.card}>
      <View style={learningStyles.cardHeading}><View style={learningStyles.cardText}><Text style={learningStyles.title}>Fundamentos Nutricionales</Text><Text style={learningStyles.summary}>Conceptos básicos para interpretar energía, nutrientes y seguimiento.</Text></View><LearningIcon name="heart-pulse" /></View>
      <EntityCardActions><EntityCardAction label="Ver Fundamentos Nutricionales" onPress={() => router.push("/system-foundations/nutrition" as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} /></EntityCardAction></EntityCardActions>
    </Card>
    <Card style={learningStyles.card}>
      <View style={learningStyles.cardHeading}><View style={learningStyles.cardText}><Text style={learningStyles.title}>Manuales de uso</Text><Text style={learningStyles.summary}>Guías breves de los módulos y flujos principales de My Scoope.</Text></View><LearningIcon name="book-marked" /></View>
      <EntityCardActions><EntityCardAction label="Ver Manuales de uso" onPress={() => router.push("/system-foundations/manuals" as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} /></EntityCardAction></EntityCardActions>
    </Card>
  </Screen>;
}
