# Imágenes remotas de alimentos

Estado: implementado; la visibilidad efectiva se comprueba en manifiesto, PNG y app instalada después de cada despliegue.

## Autoridad y alcance

`food_catalog.LegacyFoodVisualAsset` (nombre técnico histórico) es ahora la asignación editorial por `notas.Food` global activo **independiente de la fuente nutricional**. Puede cubrir tanto un alimento vinculado a `CatalogFood` como uno sin vínculo. Si ambos tienen imagen, esta asignación operacional prevalece. `food_catalog.FoodVisualAsset` mantiene las imágenes centrales ya publicadas como respaldo compatible; no crea ni corrige una ficha nutricional. El servidor conserva el PNG procesado de 256 × 256 px (sin deformar) y una variante móvil de 192 × 192 px en la base de datos para que sobrevivan a reinicios del host. El archivo fuente previo al procesamiento no se conserva. El origen/aprobación queda en `source_note`.

La API pública `/api/v1/foods/visual-assets/manifest` expone únicamente recursos publicados para alimentos globales activos. Un vínculo al catálogo central exige además que `CatalogFood` esté publicado. El ID operacional estable de cada alimento es la clave principal; el nombre original o localizado sirve solo de respaldo para superficies antiguas que aún no pasan el ID. **Todas** las entradas del manifiesto apuntan a `/api/v1/foods/visual-assets/{uuid}/{digest}.png`, la única forma de URL aceptada por la app ya instalada. El UUID es el `catalog_ref` para el respaldo central o el `public_ref` permanente de la asignación operacional; el digest SHA-256 cambia al reemplazar los bytes móviles. La antigua ruta `/legacy/{food_id}/{digest}.png` sigue disponible para compatibilidad, pero no se publica en el manifiesto. La respuesta entrega el PNG de 192 × 192 px; la versión de 256 px se conserva sin enviarse a la app. Los alimentos sin recurso, las imágenes no publicadas y los fallos de red conservan el emoji actual en la app.

La variante de visualización ancha es optativa: `manifest?layout=wide-v1` entrega URLs `/api/v1/foods/visual-assets/{uuid}/{digest}/wide-v1.png`. El servidor deriva un PNG transparente de 192 × 127 px desde los bytes móviles ya aprobados, recortando solo márgenes alfa exteriores y escalando proporcionalmente. No sobrescribe ni vuelve a aprobar el original, no cambia nutrientes ni snapshots, y usa el mismo digest de contenido más el identificador `wide-v1` para invalidar caché si cambia la fuente o el algoritmo. El manifiesto sin parámetro y las URLs cuadradas anteriores permanecen disponibles para versiones ya instaladas. La app nueva reserva 62 × 41 pt en títulos, 36 × 24 pt en compactos y 30 × 20 pt en paneles. La sustitución remota conserva la misma identidad editorial y puede revisarse por separado para ajustes particulares.

## Salida coordinada de la variante ancha

1. Integrar y desplegar el backend primero. Verificar en staging que el manifiesto sin parámetro y los PNG cuadrados no cambien, y que `?layout=wide-v1` y sus PNG respondan para imágenes centrales y asignaciones globales directas. Revisar visualmente la grilla completa antes de producción.
2. Promover el backend por el flujo normal de staging a main y comprobar las variantes públicas en producción. Las apps ya instaladas siguen solicitando la versión cuadrada, por lo que no hay cambio visual previo a la build.
3. Recién entonces generar y probar una build móvil que incluya el manifiesto ancho, los marcos proporcionales y el tratamiento sin parpadeo. Validar tarjetas, detalles, paneles, nombres largos y la sustitución remota en dispositivo.
4. Si la build falla, mantener la versión anterior; no es necesario revertir imágenes. Si falla el servidor ancho, retirar esa variante sin tocar las fuentes cuadradas. Los ajustes individuales posteriores siguen siendo cambios editoriales de imagen, no cambios nutricionales.

El cliente refresca el manifiesto como máximo una vez por minuto mientras haya iconos montados. Un cambio de PNG modifica su URL por hash y se ve sin reinstalar la app **después de que el usuario haya instalado una versión que incluya el componente remoto**. El recurso antiguo puede dejar de estar disponible tras un reemplazo; el fallback es el emoji hasta el siguiente manifiesto. No se usa el almacenamiento efímero del servidor ni URLs externas arbitrarias.

## Operación editorial

1. En Django Admin, seleccionar «Imágenes de alimentos globales» y buscar el `notas.Food` global activo, cualquiera sea su fuente. El modelo central anterior permanece disponible para mantener las imágenes existentes, pero una asignación operacional publicada tiene prioridad.
2. Cargar un PNG fuente de hasta 5 MB y 2048 × 2048 px; el servidor crea sin deformar un lienzo transparente conservado de 256 × 256 px y otro móvil de 192 × 192 px (máximo 512 KB por variante). Registrar origen y aprobación en `source_note`.
3. Guardar como borrador (`is_published=False`), revisar el icono reducido en la app de staging y luego publicar. El Admin rechaza publicación de un alimento no publicado o sin procedencia.
4. Verificar manifiesto, URL PNG y visualización en un dispositivo con la versión móvil compatible.
5. Para revertir, desmarcar `is_published`; el manifiesto deja de listar la imagen y la app vuelve al emoji en el siguiente refresco. Para sustituir, cargar otro PNG en la misma ficha; no se modifican datos nutricionales ni snapshots.

Limitación: algunas superficies legadas no transportan todavía el ID del alimento y usan nombre como respaldo. Dos alimentos con el mismo nombre visible podrían compartir imagen allí; deben migrarse esas superficies al ID. Las preparaciones y comidas no están incluidas en este contrato. Un alimento sin imagen editorial aprobada conserva su emoji; el sistema no genera imágenes automáticamente.
