import type { ComponentProps } from "react";
import { ScrollView } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { useScreenBottomSpacing } from "./screen-bottom-spacing";

export function AdaptiveScrollView({ contentContainerStyle, ...props }: ComponentProps<typeof ScrollView>) {
  const bottomSpacing = useScreenBottomSpacing();
  return <ScrollView showsVerticalScrollIndicator={false} {...props} contentContainerStyle={[contentContainerStyle, { paddingBottom: bottomSpacing }]} />;
}

export function AdaptiveNestableScrollContainer({ contentContainerStyle, ...props }: ComponentProps<typeof NestableScrollContainer>) {
  const bottomSpacing = useScreenBottomSpacing();
  return <NestableScrollContainer showsVerticalScrollIndicator={false} {...props} contentContainerStyle={[contentContainerStyle, { paddingBottom: bottomSpacing }]} />;
}
