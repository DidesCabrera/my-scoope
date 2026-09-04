import { File } from "expo-file-system";
import { ImageManipulator, SaveFormat } from "expo-image-manipulator";

export type PreparedLabelImage = {
  uri: string;
  width: number;
  height: number;
  base64: string;
  contentType: "image/jpeg";
};

const MAX_BASE64_LENGTH = 1_950_000;

function resizedDimensions(width: number, height: number, maximum: number) {
  const longest = Math.max(width, height);
  if (longest <= maximum) return {};
  return width >= height ? { width: maximum } : { height: maximum };
}

async function render(uri: string, width: number, height: number, maximum: number, compress: number) {
  const context = ImageManipulator.manipulate(uri);
  const resize = resizedDimensions(width, height, maximum);
  if (resize.width || resize.height) context.resize(resize);
  const image = await context.renderAsync();
  return image.saveAsync({ base64: true, compress, format: SaveFormat.JPEG });
}

export async function prepareLabelImage(uri: string, width: number, height: number): Promise<PreparedLabelImage> {
  let result = await render(uri, width, height, 2048, 0.84);
  if (!result.base64) throw new Error("prepared_image_missing_base64");
  if (result.base64.length > MAX_BASE64_LENGTH) {
    const firstUri = result.uri;
    result = await render(firstUri, result.width, result.height, 1600, 0.7);
    deleteCachedImage(firstUri);
  }
  if (!result.base64 || result.base64.length > MAX_BASE64_LENGTH) {
    deleteCachedImage(result.uri);
    throw new Error("prepared_image_too_large");
  }
  return {
    uri: result.uri,
    width: result.width,
    height: result.height,
    base64: result.base64,
    contentType: "image/jpeg",
  };
}

export function deleteCachedImage(uri: string | null | undefined) {
  if (!uri?.startsWith("file:")) return;
  try {
    new File(uri).delete();
  } catch {
    // Expo cache files can already have been removed by the native OCR module.
  }
}
