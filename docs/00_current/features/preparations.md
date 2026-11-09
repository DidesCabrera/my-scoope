# Preparaciones curadas

Una Preparación es un componente de Comida con ingredientes y rendimiento propios. La autoridad central es `CatalogPreparation`; `notas.Preparation` es su copia operacional. El contrato aceptado está en [0207](../../20_decisions/0207-curated-preparations-as-meal-components.md).

## Curación y entrega

1. Crear una `CatalogPreparation` y una revisión borrador en el administrador del catálogo. Registrar alimentos ingredientes en gramos, estado de preparación, condimentos, rendimiento final estimado, porción doméstica y evidencia. Los ingredientes deben ser alimentos publicados y coincidir en estado con su ficha nutricional.
2. Publicar la revisión con la acción de administrador. La operación exige sodio y evaluación de alérgenos para cada ingrediente, calcula nutrientes una sola vez y congela una suma de control. Una corrección requiere una revisión nueva.
3. Construir y aprobar un release Food Catalog. El esquema v3 incluye las Preparaciones publicadas. Si cambió la ficha de un alimento ingrediente, el release exige publicar antes una nueva revisión de la Preparación.
4. Importar el release en el consumidor con `import_food_catalog_release --materialize`, después de revisar el dry run. El importador materializa primero `notas.Food`, luego `notas.Preparation`, en una sola transacción. Sin `--materialize` solo actualiza el espejo local.

No existe carga automática desde Sheets ni se incluyen datos chilenos reales en esta entrega.

## Uso

La API móvil ofrece búsqueda y detalle en `GET /api/v1/preparations` y `GET /api/v1/preparations/{id}`. El detalle acepta `units` o `grams` y devuelve ingredientes proporcionales, nutrientes, sodio, alérgenos y evidencia. Las operaciones de Comida usan `/api/v1/library/meals/{id}/preparations`; solo aceptan una Preparación global activa o, cuando se implemente el siguiente flujo, una Preparación personal del propietario.

La biblioteca móvil muestra las Preparaciones aparte de los Alimentos y permite agregarlas o ajustar su porción. Las copias de Comida conservan la relación. Las minutas y programas reciben la nutrición actualizada cuando se materializa una revisión nueva; el menú conserva el nombre de la Preparación y el resumen de ingredientes suma las cantidades servidas para compras. El calendario conserva su snapshot anterior, incluso si la biblioteca cambia después.

Las ediciones directas de una Preparación dentro de un día calendarizado, el flujo web y la autoría personal requieren interfaces posteriores. Los comandos heredados de edición de Alimentos rechazan una Preparación calendarizada para impedir una actualización parcial de sus ingredientes o sodio.
