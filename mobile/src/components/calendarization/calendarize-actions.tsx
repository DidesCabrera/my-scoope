import { type Href, useRouter } from "expo-router";
import { CalendarDays } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function CalendarizeActions({ onClose, origin, visible }: { onClose(): void; origin?: "home"; visible: boolean }) {
  const router = useRouter();
  const navigate = (href: Href) => {
    onClose();
    router.push(href);
  };

  return <ActionSheetModal onRequestClose={onClose} visible={visible}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
      <ActionSheetHeader icon={CalendarDays} onClose={onClose} title="Calendarizar" />
      <View style={styles.content}>
        <ActionSheetActions>
          <ActionSheetAction iconNode={<EntityIcon entity="dailyPlan" size="compact" />} label="Minutas" onPress={() => navigate((origin === "home" ? "/calendar/select-plans?origin=home" : "/calendar/select-plans") as Href)} />
          <ActionSheetAction iconNode={<EntityIcon entity="program" size="compact" />} label="Programas" onPress={() => navigate("/program/activate" as Href)} />
          {commitmentKinds.map((kind) => {
            const presentation = commitmentPresentation[kind];
            const Icon = presentation.icon;
            return <ActionSheetAction iconNode={<Icon color={presentation.color} size={18} />} key={kind} label={presentation.label} onPress={() => navigate(`/calendar/commitments?kind=${kind}${origin === "home" ? "&origin=home" : ""}` as Href)} />;
          })}
        </ActionSheetActions>
      </View>
    </SafeAreaView>
  </ActionSheetModal>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
});
