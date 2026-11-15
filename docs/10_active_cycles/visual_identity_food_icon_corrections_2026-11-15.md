# Correcciones visuales propuestas · lote 2026-11-15

Estado: **candidatos para revisión editorial, no publicados**. Los PNG originales generados con la herramienta integrada de imágenes están en `assets/visual_identity_catalog/`; sus nombres terminan en `-candidate.png`. No modificar nutrientes ni inferir equivalencia de fichas por el nombre.

## Asignaciones propuestas para fichas globales

La consulta de solo lectura a producción del 15-11-2026 identificó los siguientes `CatalogFood` y `notas.Food`. Los ID operacionales se registran para evitar asignaciones por nombre ambiguo.

| Ficha visible | Food ID / CatalogFood ID | Propuesta | Estado |
|---|---:|---|---|
| Acelga cocida | 237 / 141 | Reutilizar la imagen publicada de Acelga cruda (Food 303 / CatalogFood 207). | Reutilización pendiente de revisión y publicación. |
| Acelga cruda | 303 / 207 | Mantener su imagen publicada. | Sin cambio. |
| Ajo verde crudo | No encontrada como ficha global | `green-garlic-raw-candidate.png`; reconocer primero la ficha exacta que ve el usuario. | Identidad pendiente; no asignar por similitud con Ajo crudo. |
| Pechuga de pollo cocida | 114 / 10 | `chicken-breast-roasted-candidate.png`, pechuga deshuesada asada. | Revisión visual y semántica: confirmar si el icono asado representa correctamente la ficha genérica «cocida». |
| Arándanos | 130 / 26 y legado 3 / sin vínculo | `blueberries-candidate.png`. | Resolver duplicidad operacional antes de publicar para ambos ID. |
| Arroz blanco cocido | 106 / 2 | Mantener la representación actual. | Sin cambio. |
| Arroz integral cocido | 107 / 3 | `brown-rice-cooked-candidate.png`, granos beige/café claro. | Revisión visual pendiente. |
| Arvejas verdes cocidas | 240 / 144 | `green-peas-cooked-candidate.png`. | Revisión visual pendiente. |
| Arvejas de ojo negro cocidas | 154 / 58 | Reutilizar como primer paso la imagen publicada de Arvejas de ojo negro secas (Food 233 / CatalogFood 137); evaluar después si el estado cocido requiere variante propia. | Reutilización pendiente de revisión. |
| Arvejas de ojo negro secas | 233 / 137 | Mantener su imagen publicada. | Sin cambio. |
| Betarraga cocida | 310 / 214 | Reutilizar como primer paso la imagen publicada de Betarraga cruda (Food 245 / CatalogFood 149); evaluar después variante cocida. | Reutilización pendiente de revisión. |
| Betarraga cruda | 245 / 149 | Mantener su imagen publicada. | Sin cambio. |
| Bok choy crudo | 222 / 126 | `bok-choy-raw-candidate.png`, con tallos blancos anchos y hojas lisas. | Sustituir la imagen actual solo tras revisión visual. |
| Bok choy cocido | 271 / 175 | `bok-choy-cooked-candidate.png`, hojas marchitas y tallos blancos. | Revisión visual pendiente. |
| Champiñón blanco crudo | 145 / 49 | `button-mushroom-raw-candidate.png`. | Revisión visual pendiente. |
| Champiñón blanco cocido | 209 / 113 | `button-mushroom-cooked-candidate.png`. | Revisión visual pendiente. |
| Champiñón crimini crudo | 287 / 191 | `crimini-mushroom-raw-candidate.png`, sombrero café. | Revisión visual pendiente. |
| Champiñones, legado | 54 / sin vínculo | No asignar automáticamente: primero confirmar la identidad de esa ficha. | Excepción de duplicidad/alcance. |

## Regla de publicación

La aprobación de este documento no equivale a publicación. Antes de entregar remotamente: confirmar identidad de cada Food, revisión de los candidatos a tamaño real (aprox. 41 px), fondo transparente y ausencia de halos; generar derivado móvil optimizado; asignar por ID a `FoodVisualAsset` o `LegacyFoodVisualAsset` según corresponda; verificar manifiesto y PNG en dispositivo. Registrar `source_note`, hash, estado publicado y reversión. La publicación de una imagen no altera la ficha nutricional ni sus snapshots.
