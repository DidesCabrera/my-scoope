# Preparaciones curadas y personales

Una Preparación es un componente de Comida con ingredientes y rendimiento propios. La autoridad central es `CatalogPreparation`; `notas.Preparation` es su copia operacional. El contrato aceptado está en [0207](../../20_decisions/0207-curated-preparations-as-meal-components.md).

## Curación y entrega

1. Crear una `CatalogPreparation` y una revisión borrador en el administrador del catálogo. Registrar alimentos ingredientes en gramos, estado de preparación, condimentos, rendimiento final estimado, porción doméstica y evidencia. Los ingredientes deben ser alimentos publicados y coincidir en estado con su ficha nutricional.
2. Publicar la revisión con la acción de administrador. La operación exige sodio y evaluación de alérgenos para cada ingrediente, calcula nutrientes una sola vez y congela una suma de control. Una corrección requiere una revisión nueva.
3. Construir y aprobar un release Food Catalog. El esquema v3 incluye las Preparaciones publicadas. Si cambió la ficha de un alimento ingrediente, el release exige publicar antes una nueva revisión de la Preparación.
4. Importar el release en el consumidor con `import_food_catalog_release --materialize`, después de revisar el dry run. El importador materializa primero `notas.Food`, luego `notas.Preparation`, en una sola transacción. Sin `--materialize` solo actualiza el espejo local.

No existe carga automática desde Sheets. El piloto de staging `seed_completo_italiano_pilot` agrega un Completo italiano real y acotado (no se ejecuta automáticamente en despliegues): pan de completo 45 g, vienesa tradicional PF 50 g, palta 40 g, tomate 30 g y mayonesa regular 14 g; rendimiento estimado 179 g por unidad mediana. Unidades y pesos de palta/tomate son un estándar editorial provisional, no una medición de restaurante. Los nutrientes de pan y mayonesa usan equivalentes genéricos USDA FNDDS ([pan](https://fdc.nal.usda.gov/food-details/2707656/nutrients), [mayonesa](https://fdc.nal.usda.gov/food-details/2710204/nutrients), datos CC0); la vienesa usa la [etiqueta PF](https://tiendapfalimentos.cl/salchichas-tradicional-pf-24x250gr.html). El nombre chileno no implica que la composición genérica sea idéntica a una marca local. PF declara soya y posible contacto cruzado con leche y huevo; la ficha de la Preparación lo advierte. La evaluación `none` para Palta/Tomate significa ausencia de ingredientes alergénicos mayores identificados, no garantía clínica de ausencia de alergia.

Para publicar el piloto, validar primero el comando sin `--apply`, aplicarlo en la autoridad central, construir y aprobar un release con versión nueva, probar la importación con `--dry-run` y finalmente importarlo con `--materialize` en el consumidor staging. Verificar las cinco fichas, la Preparación y su detalle en la API y en la app. Si se retira, desactivar únicamente `CatalogPreparation` del piloto en la autoridad, generar un release posterior y materializarlo; el importador desactiva la copia operacional sin borrar el historial de Comidas. Los tres alimentos nuevos pueden quedar publicados o deprecarse por el flujo normal tras revisar dependencias; nunca eliminarlos directamente. Este lote no autoriza publicación en producción sin revisión editorial de pesos, fuentes y alérgenos de producto.

## Uso

La API móvil ofrece búsqueda y detalle en `GET /api/v1/preparations` y `GET /api/v1/preparations/{id}`. El detalle acepta `units` o `grams` y devuelve ingredientes proporcionales, nutrientes, sodio, alérgenos y evidencia. Las operaciones de Comida usan `/api/v1/library/meals/{id}/preparations`; aceptan una Preparación global activa o una Preparación personal activa del propietario cuando este tiene acceso.

La biblioteca móvil muestra las Preparaciones aparte de los Alimentos y permite agregarlas o ajustar su porción. Las copias de Comida conservan la relación. Las minutas y programas reciben la nutrición actualizada cuando se materializa una revisión nueva; el menú conserva el nombre de la Preparación y el resumen de ingredientes suma las cantidades servidas para compras.

Al calendarizar, cada Preparación queda congelada dentro del snapshot del día con identidad, versión, porción, ingredientes, evidencia, alérgenos y nutrientes propios. La app la presenta como Preparación tanto en la tarjeta de la minuta como en el detalle de la comida en curso. Desde ese detalle se puede abrir su ficha, agregar otra, editar su porción, reemplazarla o quitarla; estas acciones modifican únicamente esa instancia calendarizada y recalculan los totales de su comida y del día. Los comandos heredados de edición de Alimentos siguen rechazando una Preparación para impedir actualizaciones parciales de ingredientes o sodio. El flujo web continúa fuera de alcance.

## Preparaciones personales Pro

`PERSONAL_PREPARATIONS_FEATURE_ENABLED` es la variable oficial de disponibilidad del producto, desactivada por defecto. Con ella habilitada, el permiso comercial `can_use_personal_preparations` del plan Pro permite crear, consultar, editar y retirar Preparaciones personales. El servidor aplica ambos controles; la app muestra «Mis Preparaciones» en el sidebar con badge Pro para planes inferiores, contador, búsqueda, cards, detalle y formulario. La sección lista solo las Preparaciones propias; el selector de Comidas combina las globales curadas con las personales disponibles para el usuario.

El formulario registra nombre, alimentos ingredientes en gramos, rendimiento final y porción doméstica. Usa únicamente alimentos activos y accesibles al propietario con base nutricional en gramos. Congela nombres, cantidades y macros de los ingredientes en una versión operacional; calcula nutrientes desde esa copia. El sodio queda sin dato si algún ingrediente no lo tiene y los alérgenos personales quedan explícitamente sin evaluación. No se presenta la estimación personal como curación editorial.

Cada edición crea una versión inmutable y actualiza las Comidas vivas y sus minutas/programas derivados. Los días ya calendarizados mantienen su snapshot. Eliminar retira la Preparación de la biblioteca y del selector sin borrar sus versiones; el propietario Pro todavía puede abrir su ficha desde una Comida existente. Deshabilitar la variable o perder Pro cierra la biblioteca, la ficha personal y la selección, sin borrar registros ni modificar composiciones históricas.

La eliminación de cuenta borra las Preparaciones personales, sus versiones e ingredientes antes de borrar los Alimentos privados que referenciaban. Las copias globales del catálogo permanecen operativas.

Esta primera versión no comparte una Comida que contenga una Preparación personal: el contrato de compartir actual solo admite Preparaciones globales. Tampoco permite Preparaciones anidadas ni edición web.
