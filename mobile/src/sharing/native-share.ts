import * as Clipboard from "expo-clipboard";
import { Platform, Share } from "react-native";

import type { ShareResource } from "@/api/types";

export function shareMessage(resource: ShareResource): string {
  return `Mira “${resource.title}” en MyScoope: ${resource.public_url}`;
}

export async function openNativeShare(resource: ShareResource): Promise<void> {
  if (!resource.public_url) throw new Error("share_public_url_missing");
  if (Platform.OS === "web") {
    await Clipboard.setStringAsync(resource.public_url);
    return;
  }
  await Share.share({
    message: shareMessage(resource),
    title: resource.title,
    ...(Platform.OS === "ios" ? { url: resource.public_url } : {}),
  });
}

export async function copyShareLink(resource: ShareResource): Promise<void> {
  if (!resource.public_url) throw new Error("share_public_url_missing");
  await Clipboard.setStringAsync(resource.public_url);
}
