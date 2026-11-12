# VIC00–VIC06 · Catálogo de identidad visual de entidades nutricionales

Status: planned (exploración y piloto, sin cambios de producto aprobados)
Date: 2026-11-12
Owner: Product + Catalog Operations; implementación posterior con Mobile y Backend

## Problema y resultado esperado

Las imágenes deben ayudar a reconocer alimentos y preparaciones sin sustituir sus
nombres. Hoy el icono de tipo de entidad (por ejemplo, la olla de «Preparación»)
convive con emojis alimentarios; no existe aún una biblioteca gobernada de
ilustraciones específicas. El resultado buscado es una identidad coherente,
reutilizable y corregible para Alimentos, Preparaciones y, tras aclarar su
autoridad y titularidad, Comidas.

La pregunta de producto no es «¿cómo dibujar 271 imágenes?», sino «¿qué
distinciones visuales ayudan realmente al usuario y cuáles pueden compartir una
misma ilustración sin inducir a error?».

## Estado observado (12 de noviembre de 2026)

- Autoridad Food Catalog: 222 `CatalogFood` publicados; 219 tienen `emoji` y
  `visual_key` persistidos y hay 67 claves no vacías distintas. De las claves
  genéricas, `vegetable_generic` cubre 48 fichas, `legume_generic` 26 y
  `fruit_generic` 20. Una clave no equivale todavía a un archivo de imagen.
- Producción: 222 snapshots de Food Catalog más 49 alimentos globales heredados
  visibles. La identidad visual de los 49 debe conciliarse con la autoridad antes
  de producir ilustraciones definitivas para ellos.
- `core/food_visual_identity.py` infiere emoji y clave por nombre/grupo cuando
  faltan valores; `mobile/src/components/nutrition/food-visual-icon.tsx` vuelve a
  inferir y finalmente renderiza un carácter emoji, no un activo ilustrado.
  `Pan de completo` ilustra la diferencia: su maestro no tiene clave ni emoji
  persistidos, pero el snapshot operativo expone `bread` y 🍞 por inferencia.
- Preparaciones: hay una preparación global activa. `CatalogPreparation` no tiene
  aún una asignación visual específica; Cooking Pot representa la *entidad*, no
  la apariencia de cada receta. No se encontró una biblioteca de archivos de
  alimentos integrada en la app actual. Los prototipos previos de acelga y
  garbanzo sí fueron recuperados como archivos fuente; véase abajo.
- Comidas: no se debe asumir que comparten autoridad con CatalogFood ni que una
  comida personal tiene ilustración publicable para todos. Su regla visual queda
  abierta hasta revisar el contrato de propiedad y reutilización.

## Estado del arte aplicable

- Apple recomienda imágenes reconocibles a tamaños reales, variantes de
  resolución acordes con la pantalla y pruebas en dispositivos; aumentar píxeles
  no compensa detalles ilegibles: https://developer.apple.com/design/human-interface-guidelines/images
- USWDS distingue un icono funcional de una ilustración de contenido, recomienda
  consistencia de significado y mantener texto para desambiguar:
  https://designsystem.digital.gov/components/icon/
- W3C distingue imagen informativa y decorativa; cuando el nombre ya comunica el
  alimento, el lector de pantalla no debe recibir una repetición inútil del emoji:
  https://www.w3.org/WAI/tutorials/images/
- Expo Image documenta caché y carga remota; una URL/version de activo nueva evita
  servir una imagen anterior desde caché. Es una opción técnica por evaluar, no
  una dependencia instalada actualmente:
  https://docs.expo.dev/versions/v58.0.0/sdk/image/

## Hipótesis de diseño y límites

1. Mantener dos capas: símbolo del **tipo de entidad** (alimento, preparación,
   comida) y **retrato del contenido** (acelga, completo, etc.). No usar la olla
   para hacer creer que todas las preparaciones tienen la misma apariencia.
2. Curar conceptos visuales, no generar automáticamente un archivo por ficha ni
   por alias. Separar variantes crudo/cocido/seco cuando cambie lo reconocible.
3. Probar un estilo de silueta legible, pocos detalles, fondo transparente y sin
   texto incrustado, en tamaño real de lista, card y detalle, con tema claro y
   oscuro. El primer máster raster puede ser cuadrado de 256 × 256 px; la decisión
   final de formato y distribución depende del piloto y de la plataforma.
4. Preservar un respaldo (emoji o símbolo genérico) mientras falte un activo o
   falle su carga; nunca ocultar el nombre textual.
5. Registrar por activo: concepto visual, tipo de entidad, identificador estable,
   variante, archivo/hash, versión, autoría/licencia, estado de revisión, fecha,
   aprobador y fallback. Los binarios no deben vivir en campos de la base de datos.
6. Distinguir la aprobación editorial de la entrega técnica. Un cambio de imagen
   no debe alterar nutrientes ni reescribir snapshots nutricionales históricos.
   La forma exacta de publicar y versionar imágenes requiere una decisión técnica
   explícita tras el piloto.

## Piloto: 13 alimentos globales ya visibles en producción

Todos los nombres fueron comprobados en `notas.Food` de producción y enlazan con
un maestro publicado. «No resuelto» significa representación visual demasiado
genérica o ambigua, no que falte la ficha nutricional.

| # | Alimento | Visual actual | Pregunta que debe resolver el piloto |
|---|---|---|---|
| 1 | Acelga cruda | 🥬 / `vegetable_generic` | ¿Silueta propia de acelga? |
| 2 | Acelga cocida | 🥬 / `vegetable_generic` | ¿Se reconoce como estado distinto del crudo? |
| 3 | Arándanos | 🍎 / `fruit_generic` | Corregir categoría visual errónea. |
| 4 | Chirimoya cruda | 🍎 / `fruit_generic` | Reconocer un fruto relevante en Chile sin manzana genérica. |
| 5 | Garbanzos secos | 🫘 / `legume_generic` | Representar grano y estado seco. |
| 6 | Garbanzos cocidos | 🫘 / `legume_generic` | Decidir si comparte retrato con el seco. |
| 7 | Tofu firme | 🫘 / `legume_generic` | Evitar que un derivado de soya parezca un poroto. |
| 8 | Almejas cocidas | 🐟 / `seafood_generic` | Corregir molusco representado como pez. |
| 9 | Trucha arcoíris cruda | 🐟 / `seafood_generic` | Distinguir pez específico de un pescado genérico. |
| 10 | Pan de completo | 🍞 / `bread` inferidos | Representar forma chilena y resolver metadatos no persistidos. |
| 11 | Queso azul | 🧀 / `cheese` | Determinar cuándo la variedad amerita ilustración propia. |
| 12 | Trutro de pollo crudo con piel | 🍗 / `chicken` | Representar corte y estado crudo. |
| 13 | Trutro de pollo cocido con piel | 🍗 / `chicken` | Decidir si el cocido necesita otra variante. |

Dos pruebas de extensión fuera de los 13 alimentos: **Completo italiano** como
preparación compuesta y una **Comida con alimento + preparación** para validar
jerarquía y composición, sin presupuestar aún una imagen por comida.

## Secuencia propuesta

| Etapa | Entregable | Gate de avance |
|---|---|---|
| VIC00 | Inventario reproducible de fichas, claves, superficies y activos previos | Se identifican autoridad, duplicados y fallbacks. |
| VIC01 | Guía de estilo y contrato de concepto/variante/asignación | Felipe aprueba 2–3 ejemplos contrastantes a tamaño real. |
| VIC02 | Galería de las 13 fichas + preparación/comida de prueba | Cada imagen se reconoce junto al nombre en claro/oscuro y tamaños reales. |
| VIC03 | Piloto técnico en staging, sin reemplazo masivo | Carga, caché, fallback y navegación funcionan en las superficies acordadas. |
| VIC04 | Prueba breve con usuarios chilenos y revisión editorial | No quedan asociaciones evidentemente engañosas; se registra confusión. |
| VIC05 | Registro versionado, publicación/rollback y métricas | Corrección visual reproducible sin tocar nutrición. |
| VIC06 | Ampliación por demanda, comenzando por contenido publicado | Se priorizan imágenes específicas antes que volumen bruto. |

Medidas para el piloto: cobertura **específica aprobada** (no contar genéricos
como específicos), errores de correspondencia imagen–nombre, reconocimiento en
comparaciones pequeñas, fallos de carga/fallback y costo de producir/corregir
cada concepto. El resultado de VIC02–VIC04 decidirá si se amplía, se ajusta el
estilo o se mantiene un conjunto reducido de imágenes excelentes.

## Decisiones pendientes y no objetivos

- Elegir tras el piloto si la biblioteca se distribuye con la app o como activos
  remotos versionados; evaluar peso, conexión, caché y velocidad de corrección.
- Definir la autoridad visual de Comidas personales y curadas antes de asociar
  activos a ellas; no asumir que la receta o sus ingredientes generan una imagen
  fiable por sí mismos.
- Evaluar los prototipos recuperados a tamaño real, revisar su autoría y
  reutilizarlos solo si superan la guía; aún no son activos aprobados para la app.
- No generar en masa, no sustituir nombres por imágenes, no copiar iconografía de
  terceros sin licencia y no publicar imágenes en producción durante esta etapa.

## Recuperación de prototipos previos (VIC00)

El trabajo del 22 de octubre de 2026 en el chat «Experto en Contexto» generó
dos imágenes originales para probar una identidad compartida por variantes del
mismo alimento. Se recuperaron los PNG de la carpeta de imágenes generadas de
ese chat y se guardaron aquí como evidencia duradera del piloto:

| Concepto | Archivo recuperado | Asignación propuesta entonces | SHA-256 |
|---|---|---|---|
| Acelga (`chard`) | `assets/visual_identity_catalog/chard-prototype.png` | Acelga cruda y cocida | `9ed11bf6886ea8696d2ae629e85e58130c14aa6bb52e7de9523933828cbe261d` |
| Garbanzo (`chickpea`) | `assets/visual_identity_catalog/chickpea-prototype.png` | Garbanzos secos y cocidos | `a74effef898fb1e6228ad0045b830c0be4410399bf248217550212efe24f463b` |

Ambos archivos son PNG RGBA de 1254 × 1254 px, con transparencia; el formato
final para la app sigue pendiente. En la planilla histórica [Food Catalog central
— 219 alimentos y porciones](https://docs.google.com/spreadsheets/d/13hEtHnxwfsPI0j0BuTfloPqoqaVRRSGVXAjFjNuKOoE/edit#gid=2005160404),
pestaña `Alimentos`, la columna W «Icono My Scoope (prototipo)» insertó estos
ejemplos mediante fórmulas `IMAGE()` con enlaces firmados que caducaron el 23
de octubre de 2026. Por tanto, esa planilla sirve como rastro editorial, no como
almacenamiento estable de los binarios. La columna X registra las claves
`chard` y `chickpea`; en ese trabajo la revisión de Felipe quedó «Pendiente».

Estas imágenes son **prototipos generados para My Scoope**, no una aprobación
editorial ni una confirmación de exclusividad o protección jurídica. Antes de
usarlas en producto hay que comparar su legibilidad a 24–40 px, la coherencia
entre ambos conceptos y la exactitud visual de las variantes crudo/cocido y
seco/cocido. La vista grande sugiere buena identificación del alimento, pero
sus sombras y detalles podrían perderse en listas pequeñas.

## Decisión visual: familia de alimentos en polvo (12 de noviembre de 2026)

Felipe aceptó conservar **todas las propuestas mostradas** en la prueba de
pantalla. Su preferencia inicial es la forma con cuchara/recipiente y polvo
visible, por encima del sobre vertiendo contenido. El sobre también queda
aceptado como opción reutilizable para otros alimentos cuya presentación
envasada sea relevante. Se registra como **aprobación conceptual de las opciones**,
no como aprobación técnica de archivos finales ni autorización de publicación.

| Concepto visual | Archivo original conservado | Uso explorado | SHA-256 |
|---|---|---|---|
| Polvo claro en cuchara | `assets/visual_identity_catalog/powder-wheat-flour-prototype.png` | Harina de trigo; extensible tras revisar harina integral y otras harinas claras | `3022639dbf3c3ca576259442d007391fc33b8642f85a254626577b5e92f146e6` |
| Polvo ocre en cuchara | `assets/visual_identity_catalog/powder-maca-scoop-prototype.png` | Maca andina molida; ejemplo de diseño, ficha alimentaria no confirmada | `9466e9a9800dc2e1132a98d25e639528cbf6acd103c1d1b8fb088ad3b1115b66` |
| Polvo café en cuchara | `assets/visual_identity_catalog/powder-cocoa-prototype.png` | Cacao en polvo; ejemplo de diseño, ficha alimentaria no confirmada | `2d4335e8d608e008058194b2c9243bbc5b033497781845838518ab5a889c36c4` |
| Sobre vertiendo polvo ocre | `assets/visual_identity_catalog/powder-maca-sachet-prototype.png` | Alternativa de presentación, no asignación por defecto a maca | `3494bb403675f92018670f08f895f9d42dcb8ac9f320dee959c8c9388a8271ac` |

Se conservan los originales generados, aunque sean grandes; **no deben enviarse
tal cual a la app**. Antes de integración se prepararán derivados optimizados,
se probarán a 20/24/41 px en tema claro y oscuro y se registrará una asignación
explícita alimento → concepto/variante. La aprobación visual no cambia el estado
nutricional ni la publicabilidad de ninguna ficha. En el lote chileno, harina de
trigo, harina integral de trigo, harina de maíz y sémola de trigo seca son
candidatos registrados; maca y cacao no figuran en esa lista y no deben darse
por publicados a partir de esta exploración.

## Fuentes internas de evidencia

- `core/food_visual_identity.py`
- `food_catalog/models.py` (`CatalogFood`, `CatalogPreparation`)
- `mobile/src/components/nutrition/food-visual-icon.tsx`
- `docs/00_current/features/food_catalog.md`
- Consulta de solo lectura a Food Catalog central y producción, 2026-11-12.
- Archivos originales del chat «Experto en Contexto», 2026-10-22; comprobados
  visualmente y comparados por SHA-256 al recuperarlos el 2026-11-12.
