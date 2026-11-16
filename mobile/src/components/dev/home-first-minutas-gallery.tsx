import { StyleSheet, useWindowDimensions, View } from "react-native";

import { HomeFirstMinutasOffer } from "@/components/home/home-first-minutas-offer";
import { SectionTitle } from "@/components/ui";

export function HomeFirstMinutasGallery() {
  const { width } = useWindowDimensions();

  return <>
    <SectionTitle detail="Componente productivo · invitación posterior al onboarding" title="Inicio · invitación para 2 minutas" />
    <View style={[styles.preview, width >= 700 && styles.previewWide]}>
      <HomeFirstMinutasOffer onPress={() => undefined} />
    </View>
  </>;
}

const styles = StyleSheet.create({
  preview: { alignSelf: "stretch" },
  previewWide: { alignSelf: "center", width: 414 },
});
