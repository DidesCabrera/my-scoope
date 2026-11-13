# Imágenes remotas de alimentos

Estado: implementado en código; la publicación efectiva depende de desplegar backend, migración y una versión móvil con este soporte.

## Autoridad y alcance

`food_catalog.FoodVisualAsset` guarda una imagen PNG por `CatalogFood` publicado. Es identidad visual editorial, independiente de nutrición, porciones y snapshots `notas.Food`. El servidor conserva el PNG procesado de 256 × 256 px (sin deformar) y una variante móvil de 192 × 192 px en la base de datos para que sobrevivan a reinicios del host. El archivo fuente previo al procesamiento no se conserva. El origen/aprobación queda en `source_note`. Ninguna imagen se publica al instalar la migración.

La API pública `/api/v1/foods/visual-assets/manifest` expone únicamente recursos publicados cuyo alimento de catálogo está publicado y tiene un `notas.Food` global activo materializado. El ID operacional estable de cada alimento es la clave principal; el nombre original o localizado sirve solo de respaldo para superficies antiguas que aún no pasan el ID. Todas apuntan a una URL versionada por SHA-256 de la variante móvil. `/api/v1/foods/visual-assets/{catalog_ref}/{digest}.png` entrega el PNG de 192 × 192 px; la versión de 256 px se conserva sin enviarse a la app. Los alimentos sin recurso, las imágenes no publicadas y los fallos de red conservan el emoji actual en la app.

El cliente refresca el manifiesto como máximo una vez por minuto mientras haya iconos montados. Un cambio de PNG modifica su URL por hash y se ve sin reinstalar la app **después de que el usuario haya instalado una versión que incluya el componente remoto**. El recurso antiguo puede dejar de estar disponible tras un reemplazo; el fallback es el emoji hasta el siguiente manifiesto. No se usa el almacenamiento efímero del servidor ni URLs externas arbitrarias.

## Operación editorial

1. En Django Admin, seleccionar un `CatalogFood` publicado y abrir «Food visual assets».
2. Cargar un PNG fuente de hasta 5 MB y 2048 × 2048 px; el servidor crea sin deformar un lienzo transparente conservado de 256 × 256 px y otro móvil de 192 × 192 px (máximo 512 KB por variante). Registrar origen y aprobación en `source_note`.
3. Guardar como borrador (`is_published=False`), revisar el icono reducido en la app de staging y luego publicar. El Admin rechaza publicación de un alimento no publicado o sin procedencia.
4. Verificar manifiesto, URL PNG y visualización en un dispositivo con la versión móvil compatible.
5. Para revertir, desmarcar `is_published`; el manifiesto deja de listar la imagen y la app vuelve al emoji en el siguiente refresco. Para sustituir, cargar otro PNG en la misma ficha; no se modifican datos nutricionales ni snapshots.

Limitación inicial: algunas superficies legadas no transportan todavía el ID del alimento y usan nombre como respaldo. Dos alimentos con el mismo nombre visible podrían compartir imagen allí; deben migrarse esas superficies al ID antes de abrir imágenes privadas por usuario. Las preparaciones no están incluidas en este contrato.
