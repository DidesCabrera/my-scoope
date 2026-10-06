import { type Href, Redirect, useRouter } from "expo-router";
import { BookMarked, HeartPulse } from "lucide-react-native";
import { Text, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Screen } from "@/components/ui";
import { learningStyles } from "@/components/learning/learning-ui";
import { tokens } from "@/design/tokens";

export default function SystemFoundationsScreen() {
  const router = useRouter();
  const { status } = useSession();
  if (status === "anonymous") return <Redirect href="/login" />;
  return <Screen>
    <AppHeader eyebrow="Aprender en My Scoope" title="Fundamentos Sistema" />
    <Text style={learningStyles.intro}>Comprende los conceptos nutricionales esenciales y aprende a usar las herramientas principales del sistema.</Text>
    <Card style={learningStyles.card}>
      <View style={learningStyles.cardHeading}><HeartPulse color={tokens.color.textMain} size={26} /><View style={learningStyles.cardText}><Text style={learningStyles.title}>Fundamentos Nutricionales</Text><Text style={learningStyles.summary}>Conceptos básicos para interpretar energía, nutrientes y seguimiento.</Text></View></View>
      <Button label="Ver fundamentos" onPress={() => router.push("/system-foundations/nutrition" as Href)} variant="secondary" />
    </Card>
    <Card style={learningStyles.card}>
      <View style={learningStyles.cardHeading}><BookMarked color={tokens.color.textMain} size={26} /><View style={learningStyles.cardText}><Text style={learningStyles.title}>Manuales de uso</Text><Text style={learningStyles.summary}>Guías breves de los módulos y flujos principales de My Scoope.</Text></View></View>
      <Button label="Ver manuales" onPress={() => router.push("/system-foundations/manuals" as Href)} variant="secondary" />
    </Card>
  </Screen>;
}
