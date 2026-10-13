import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { StyleSheet } from "react-native";

import { EntityDetailMetadata } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { sharedDate } from "@/sharing/presentation";
import { useSharedResource } from "@/sharing/use-shared-resource";

export default function SharedResourceInformationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const setHeaderPresentation = useHeaderPresentation();
  const { error, loading, resource } = useSharedResource(id);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/share/${id}` as Href, mode: "back", title: "Información del elemento" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (!id) return <Redirect href="/inbox" />;
  return (
    <Screen contentStyle={loading ? styles.loadingContent : undefined} headerMode="preserve">
      {loading ? <LoadingState label="Cargando información…" mode="content" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {resource ? (
        <EntityDetailMetadata
          creator="Elemento compartido"
          creatorLabel="Origen"
          updatedAt={sharedDate(resource.created_at)}
          updatedAtLabel="Compartido"
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  loadingContent: { paddingBottom: 0, paddingTop: 0 },
});
