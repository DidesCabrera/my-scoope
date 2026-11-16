# Catálogo visual aprobado · completo, papaya y aves · 2026-11-15

Status: active

Estado: **todas las propuestas de la grilla aprobadas visualmente por Felipe el 2026-11-15; ninguna nueva imagen asignada ni publicada**. Felipe confirmó explícitamente que la similitud entre pollo y pavo molidos es aceptable porque refleja su apariencia real. El lote anterior de choclo, clara, verduras, hongos, mayonesa y melón también quedó aprobado visualmente, pero sigue sin asignarse ni publicarse. Comparación de este lote a escala de la app: [grilla 62 × 41 px](visual_identity_poultry_completo_papaya_2026-11-15.html).

Se revisaron las fichas globales activas de producción mediante consulta de solo lectura. El pan de completo usa `🍞`, la papaya cruda `🍎`, y diez de las once fichas de pollo/pavo todavía usan `🍗` sin imagen propia. **Hígado de pollo crudo** ya tiene imagen de catálogo publicada; no debe reemplazarse por un genérico. La ficha operacional heredada `Pechuga Pollo Cocida` no tiene vínculo a `CatalogFood` y también necesita asignación explícita para no quedar atrás. Los `id` indicados son operacionales de producción y deben reconfirmarse antes de cualquier publicación.

| Ficha de producción | ID | Propuesta / tratamiento | Estado |
|---|---:|---|---|
| Pan de completo | 327 | [Pan alargado abierto](assets/visual_identity_catalog/hotdog-bun-proposal.png), sin salchicha ni ingredientes. | Aprobada visualmente; no publicada |
| Papaya cruda | 299 | [Papaya tropical en estilo emoji](assets/visual_identity_catalog/raw-papaya-emoji-proposal.png), fruto entero y medio fruto con pulpa naranja y semillas oscuras. | Aprobada visualmente; no publicada |
| Completo italiano (preparación) | preparación 1 | [Completo armado](assets/visual_identity_catalog/completo-italiano-preparation-proposal.png), tomate, palta y mayonesa. | Aprobada visualmente; requiere contrato de imagen para preparaciones |
| Ala de pollo cruda con piel | 281 | [Ala cruda](assets/visual_identity_catalog/raw-chicken-wing-proposal.png), silueta doble plegada. | Aprobada visualmente; no publicada |
| Hígado de pollo crudo | 181 | Conservar imagen propia publicada (asset de catálogo 50), revisar solo si falla la representación en móvil. | Ya tiene imagen |
| Pavo molido crudo | 312 | [Carne molida de pavo](assets/visual_identity_catalog/raw-ground-turkey-proposal.png). | Aprobada visualmente; similitud con pollo molido aceptada |
| Pechuga de pavo cocida | 115 | [Pavo cocido en láminas](assets/visual_identity_catalog/cooked-turkey-slices-proposal.png), sin marcas de parrilla. | Aprobada visualmente; no publicada |
| Pechuga de pollo cocida | 114 | Reutilizar [ícono de pollo asado aprobado en lote previo](assets/visual_identity_catalog/chicken-breast-roasted-v1-approved.png). | Ya aprobado visualmente; no publicado |
| Pechuga de pollo cruda sin piel | 218 | [Filete crudo](assets/visual_identity_catalog/raw-chicken-fillet-proposal.png), rosado y sin hueso. | Aprobada visualmente; no publicada |
| Pechuga Pollo Cocida (ficha heredada) | 27 | Compartir el ícono de pechuga de pollo cocida solo tras confirmar equivalencia de ficha. | Revisión de equivalencia pendiente |
| Pollo entero crudo con piel | 278 | [Pollo entero crudo](assets/visual_identity_catalog/raw-whole-chicken-proposal.png), sin cabeza ni plumas. | Aprobada visualmente; no publicada |
| Pollo molido crudo | 168 | [Carne molida de pollo](assets/visual_identity_catalog/raw-ground-chicken-proposal.png). | Aprobada visualmente; similitud con pavo molido aceptada |
| Trutro de pollo cocido con piel | 219 | [Trutro dorado](assets/visual_identity_catalog/cooked-chicken-drumstick-proposal.png). | Aprobada visualmente; no publicada |
| Trutro de pollo crudo con piel | 150 | [Trutro rosado](assets/visual_identity_catalog/raw-chicken-drumstick-proposal.png). | Aprobada visualmente; no publicada |

## Criterios de asignación

- Prompts editoriales por activo: pan alargado abierto sin relleno; completo italiano con salchicha, tomate, palta y mayonesa; papaya tropical entera y en corte longitudinal; ala plegada cruda; pavo cocido laminado; pavo y pollo molidos en montículos separados; filete de pollo crudo deshuesado; pollo entero crudo eviscerado; trutros crudo y cocido con silueta de corte reconocible. En todos se pidió ícono 3D tipo emoji, fondo transparente, composición centrada, lectura a 41 px, sin texto ni marcas ni plato; la papaya requirió una segunda pasada para reducir el acabado fotográfico.
- La primera [versión de papaya](assets/visual_identity_catalog/raw-papaya-proposal.png) se conserva solo como antecedente de generación; **no es candidata para aprobación** por su acabado demasiado fotográfico. La grilla presenta exclusivamente la segunda versión.
- Separar especie, corte y estado. El emoji `🍗` no representa una pechuga, carne molida, un ala ni un pollo entero.
- La similitud visual entre las carnes molidas de pollo y pavo fue revisada y **aceptada expresamente por Felipe**. No se requiere una diferencia artificial adicional para aprobar o asignar estas dos imágenes; la ficha y el nombre siguen distinguiendo los alimentos.
- La propuesta de papaya se refiere a la papaya tropical de la ficha USDA `169926` registrada en el manifiesto. No adjudicarla a la papaya chilena `Vasconcellea pubescens`, que es otra especie.
- La imagen de `Completo italiano` es la primera propuesta para una preparación. El contrato operativo de imágenes remotas actual cubre alimentos, no preparaciones; la asignación/publicación requiere ampliar ese contrato y probar la entrega en móvil.
- Todos son originales editoriales con fondo transparente; no se modificaron nutrientes, recetas, snapshots ni fichas en producción. Antes de publicar: validar el ícono a 62 × 41 px, derivar el recurso móvil, resolver la identidad exacta de cada ficha y comprobar la imagen efectiva en el teléfono.

## Fuentes de identidad

- Fichas efectivas: consulta de solo lectura a `notas_food`, `food_catalog_catalogfood`, `food_catalog_foodvisualasset` y `food_catalog_legacyfoodvisualasset` en la base de producción, 2026-11-15.
- Papaya: `food_catalog/data/generic_food_coverage_manifest_v1.csv`, `fruit-papaya-cruda`, USDA SR Legacy `169926`.
- Contrato de entrega visual: `docs/00_current/features/food_visual_assets.md`.
