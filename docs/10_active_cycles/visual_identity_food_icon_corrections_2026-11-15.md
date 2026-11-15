# Correcciones visuales propuestas · lote 2026-11-15

Status: active

Estado: **propuestas aprobadas visualmente por Felipe el 15-11-2026; no publicadas**. Los PNG originales están en `assets/visual_identity_catalog/`. La primera propuesta de pechuga se conserva como `chicken-breast-roasted-v1-approved.png`; la segunda permanece como `chicken-breast-roasted-candidate.png` solo para referencia y **no fue elegida**. Las distintas imágenes de bok choy y champiñones corresponden a fichas diferentes, no a opciones por elegir. No modificar nutrientes ni inferir equivalencia de fichas por el nombre.

## Asignaciones propuestas para fichas globales

La consulta de solo lectura a producción del 15-11-2026 identificó los siguientes `CatalogFood` y `notas.Food`. Los ID operacionales se registran para evitar asignaciones por nombre ambiguo.

| Ficha visible | Food ID / CatalogFood ID | Propuesta | Estado |
|---|---:|---|---|
| Acelga cocida | 237 / 141 | Reutilizar la imagen publicada de Acelga cruda (Food 303 / CatalogFood 207). | Aprobada visualmente; pendiente de publicación. |
| Acelga cruda | 303 / 207 | Mantener su imagen publicada. | Sin cambio. |
| Ajo verde crudo | No encontrada como ficha global | `green-garlic-raw-candidate.png`; reconocer primero la ficha exacta que ve el usuario. | Imagen aprobada; identidad pendiente. No asignar por similitud con Ajo crudo. |
| Pechuga de pollo cocida | 114 / 10 | **Primera propuesta elegida:** `chicken-breast-roasted-v1-approved.png`, pechuga deshuesada asada. | Imagen aprobada; revisar fondo/halo y confirmar si representa la ficha genérica «cocida» antes de publicar. |
| Arándanos | 130 / 26 y legado 3 / sin vínculo | `blueberries-candidate.png`. | Imagen aprobada; resolver duplicidad operacional antes de publicar para ambos ID. |
| Arroz blanco cocido | 106 / 2 | Mantener la representación actual. | Sin cambio. |
| Arroz integral cocido | 107 / 3 | `brown-rice-cooked-candidate.png`, granos beige/café claro. | Imagen aprobada; pendiente de publicación. |
| Arvejas verdes cocidas | 240 / 144 | `green-peas-cooked-candidate.png`. | Imagen aprobada; pendiente de publicación. |
| Arvejas de ojo negro cocidas | 154 / 58 | Reutilizar como primer paso la imagen publicada de Arvejas de ojo negro secas (Food 233 / CatalogFood 137); evaluar después si el estado cocido requiere variante propia. | Reutilización aprobada; pendiente de publicación. |
| Arvejas de ojo negro secas | 233 / 137 | Mantener su imagen publicada. | Sin cambio. |
| Betarraga cocida | 310 / 214 | Reutilizar como primer paso la imagen publicada de Betarraga cruda (Food 245 / CatalogFood 149); evaluar después variante cocida. | Reutilización aprobada; pendiente de publicación. |
| Betarraga cruda | 245 / 149 | Mantener su imagen publicada. | Sin cambio. |
| Bok choy crudo | 222 / 126 | `bok-choy-raw-candidate.png`, con tallos blancos anchos y hojas lisas. | Imagen aprobada; pendiente de publicación. |
| Bok choy cocido | 271 / 175 | `bok-choy-cooked-candidate.png`, hojas marchitas y tallos blancos. | Imagen aprobada; pendiente de publicación. |
| Champiñón blanco crudo | 145 / 49 | `button-mushroom-raw-candidate.png`. | Imagen aprobada; pendiente de publicación. |
| Champiñón blanco cocido | 209 / 113 | `button-mushroom-cooked-candidate.png`. | Imagen aprobada; pendiente de publicación. |
| Champiñón crimini crudo | 287 / 191 | `crimini-mushroom-raw-candidate.png`, sombrero café. | Imagen aprobada; pendiente de publicación. |
| Champiñones, legado | 54 / sin vínculo | No asignar automáticamente: primero confirmar la identidad de esa ficha. | Excepción de duplicidad/alcance. |

## Regla de publicación

La aprobación de este documento no equivale a publicación. Antes de entregar remotamente: confirmar identidad de cada Food, revisión de los candidatos a tamaño real (aprox. 41 px), fondo transparente y ausencia de halos; generar derivado móvil optimizado; asignar por ID a `FoodVisualAsset` o `LegacyFoodVisualAsset` según corresponda; verificar manifiesto y PNG en dispositivo. Registrar `source_note`, hash, estado publicado y reversión. La publicación de una imagen no altera la ficha nutricional ni sus snapshots.
