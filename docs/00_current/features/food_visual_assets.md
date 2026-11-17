# Catálogo visual remoto de alimentos y preparaciones

Estado: implementado; la visibilidad efectiva se comprueba en manifiesto, PNG y app instalada después de cada despliegue.

## Autoridad y alcance

`notas.LegacyFoodVisualAsset` (nombre técnico histórico) es la asignación editorial por `notas.Food` global activo **independiente de la fuente nutricional**. Conserva la tabla histórica `food_catalog_legacyfoodvisualasset`, sus filas y los UUID públicos; el cambio de aplicación Django no copia ni recrea los PNG. Puede cubrir tanto un alimento vinculado a `CatalogFood` como uno sin vínculo. Si ambos tienen imagen, esta asignación operacional prevalece. `food_catalog.FoodVisualAsset` mantiene las imágenes centrales ya publicadas como respaldo compatible. `food_catalog.PreparationVisualAsset` vincula la imagen de una preparación al `CatalogPreparation` publicado; la app la resuelve por el ID estable de la `notas.Preparation` materializada. Los tres recursos usan el mismo procesamiento, versionado por hash, manifiesto, caché y política de publicación. Ninguno cambia nutrientes, recetas ni snapshots. El servidor conserva el PNG procesado de 256 × 256 px (sin deformar) y una variante móvil de 192 × 192 px en la base de datos para que sobrevivan a reinicios del host. El archivo fuente previo al procesamiento no se conserva. El origen/aprobación queda en `source_note`.

La API pública canónica `/api/v1/catalog/visual-assets/manifest` expone `food_ids`, `images`, `preparation_ids` y `preparation_images`. Solo lista alimentos globales activos y preparaciones globales activas con versión publicada; el vínculo al catálogo central también debe estar publicado. Los IDs operacionales son la clave principal y los nombres sirven de respaldo para superficies sin ID. La ruta anterior `/api/v1/foods/visual-assets/manifest` devuelve el mismo contenido para compatibilidad con builds instaladas. Los alimentos conservan sus URLs `/api/v1/foods/visual-assets/{uuid}/{digest}.png`; las preparaciones usan `/api/v1/preparations/visual-assets/{uuid}/{digest}.png`. El digest SHA-256 cambia al reemplazar los bytes móviles. La antigua ruta `/legacy/{food_id}/{digest}.png` sigue disponible para compatibilidad, pero no se publica en el manifiesto. La respuesta entrega el PNG de 192 × 192 px; la versión de 256 px se conserva sin enviarse a la app. Los recursos ausentes o no publicados conservan el icono anterior.

La variante de visualización ancha es optativa: `manifest?layout=wide-v1` entrega URLs `.../{uuid}/{digest}/wide-v1.png` de ambas entidades. El servidor deriva un PNG transparente de 192 × 127 px desde los bytes móviles ya aprobados, recortando solo márgenes alfa exteriores y escalando proporcionalmente. No sobrescribe ni vuelve a aprobar el original, no cambia nutrientes ni snapshots, y usa el mismo digest de contenido más el identificador `wide-v1` para invalidar caché si cambia la fuente o el algoritmo. El manifiesto sin parámetro y las URLs cuadradas anteriores permanecen disponibles para versiones ya instaladas. La app reserva 62 × 41 pt en títulos, 36 × 24 pt en compactos y 30 × 20 pt en paneles para ambas entidades.

La web también consulta el manifiesto compatible `foods/visual-assets/manifest?layout=wide-v1` para tarjetas y detalles de alimentos, y para sus filas dentro de comidas y preparaciones. Usa el ID operacional cuando está disponible; solo los snapshots sin ID recurren al nombre. La app móvil consulta el manifiesto canónico y usa el mismo caché y estado de carga para alimentos y preparaciones. Ambas validan rutas versionadas antes de cargar imágenes.

## Salida coordinada de la variante ancha

1. Integrar y desplegar el backend primero. Verificar en staging que el manifiesto sin parámetro y los PNG cuadrados no cambien, y que `?layout=wide-v1` y sus PNG respondan para imágenes centrales y asignaciones globales directas. Revisar visualmente la grilla completa antes de producción.
2. Promover el backend por el flujo normal de staging a main y comprobar las variantes públicas en producción. Las apps ya instaladas siguen solicitando la versión cuadrada, por lo que no hay cambio visual previo a la build.
3. Recién entonces generar y probar una build móvil que incluya el manifiesto ancho, los marcos proporcionales y el tratamiento sin parpadeo. Validar tarjetas, detalles, paneles, nombres largos y la sustitución remota en dispositivo.
4. Si la build falla, mantener la versión anterior; no es necesario revertir imágenes. Si falla el servidor ancho, retirar esa variante sin tocar las fuentes cuadradas. Los ajustes individuales posteriores siguen siendo cambios editoriales de imagen, no cambios nutricionales.

El cliente refresca el manifiesto como máximo una vez por minuto mientras haya iconos montados. Un cambio de PNG modifica su URL por hash y se ve sin reinstalar la app **después de que el usuario haya instalado una versión que incluya el componente remoto**. El recurso antiguo puede dejar de estar disponible tras un reemplazo; el fallback es el emoji hasta el siguiente manifiesto. No se usa el almacenamiento efímero del servidor ni URLs externas arbitrarias.

## Revisión de escala visual

La **Grilla de escala visual** es la revisión comparativa recurrente de las imágenes remotas publicadas: 15 alimentos identificados por fila, una vista con el marco actual y otra con el marco rectangular propuesto. El procedimiento reproducible está en `.codex/skills/food-icon-scale-audit/`. No incluye automáticamente alimentos sin imagen remota ni candidatos sin publicar.

Felipe prefirió visualmente el marco de **62 × 41 pt**, ya implementado en la app para títulos de alimentos y preparaciones. La derivación ancha recorta margen transparente y escala el dibujo sin deformarlo. Las revisiones individuales de tamaño siguen siendo editoriales.

## Operación editorial

1. En Django Admin, seleccionar «Imágenes de alimentos globales» y buscar el `notas.Food` global activo, cualquiera sea su fuente. El modelo central anterior permanece disponible para mantener las imágenes existentes, pero una asignación operacional publicada tiene prioridad.
2. Cargar un PNG fuente de hasta 5 MB y 2048 × 2048 px; el servidor crea sin deformar un lienzo transparente conservado de 256 × 256 px y otro móvil de 192 × 192 px (máximo 512 KB por variante). Registrar origen y aprobación en `source_note`.
3. Guardar como borrador (`is_published=False`), revisar el icono reducido en la app de staging y luego publicar. El Admin rechaza publicación de un alimento no publicado o sin procedencia.
4. Verificar manifiesto, URL PNG y visualización en un dispositivo con la versión móvil compatible.
5. Para revertir, desmarcar `is_published`; el manifiesto deja de listar la imagen y la app vuelve al emoji en el siguiente refresco. Para sustituir, cargar otro PNG en la misma ficha; no se modifican datos nutricionales ni snapshots.

Para publicar una preparación, seleccionar una `CatalogPreparation` activa con versión publicada, cargar el PNG en `PreparationVisualAsset` y registrar su aprobación. Verificar `preparation_ids`, la URL cuadrada y ancha, y su aparición en cards, detalle y paneles de la build compatible. La publicación del catálogo visual es independiente de la publicación nutricional: una ficha nueva de alimento debe aprobarse en Food Catalog, incluirse en una release e importarse como `notas.Food` antes de asignar su imagen en el consumidor.

Limitación: algunas superficies legadas no transportan todavía el ID del alimento y usan nombre como respaldo. Dos alimentos con el mismo nombre visible podrían compartir imagen allí; deben migrarse esas superficies al ID. Las comidas no tienen imagen editorial en este contrato. El sistema no genera imágenes automáticamente.
