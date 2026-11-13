type Manifest = { images?: Record<string, string>; food_ids?: Record<string, string> };

const IMAGE_PATH = /^\/api\/v1\/foods\/visual-assets\/[0-9a-f-]{36}\/[0-9a-f]{64}\.png$/;

export function normalizeFoodVisualName(name: string): string {
  return name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLocaleLowerCase("es").replace(/\s+/g, " ");
}

export function parseFoodVisualManifest(payload: Manifest, baseUrl: string): Map<string, string> {
  const result = new Map<string, string>();
  for (const [name, path] of Object.entries(payload.images ?? {})) {
    if (IMAGE_PATH.test(path)) result.set(`name:${normalizeFoodVisualName(name)}`, `${baseUrl}${path}`);
  }
  for (const [id, path] of Object.entries(payload.food_ids ?? {})) {
    if (/^[1-9]\d*$/.test(id) && IMAGE_PATH.test(path)) result.set(`id:${id}`, `${baseUrl}${path}`);
  }
  return result;
}
