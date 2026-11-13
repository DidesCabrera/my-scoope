# Suplementos

Status: local implementation, pending staging integration

## Catálogo global inicial

`SupplementCatalogEntry` conserva las fichas editoriales globales con fuente,
fecha de revisión y estado de publicación. Explorar muestra solo fichas publicadas
a usuarios con acceso a Suplementos Pro. Guardar crea una copia personal independiente;
las ediciones del usuario no cambian el catálogo. La primera ficha es una referencia
genérica de vitamina D3, sin marca, dosis ni composición comercial. Su fuente
identifica la forma D3; no demuestra las características de un producto concreto.

Para agregar productos de marca, curación debe registrar identidad del fabricante,
nombre y presentación exactos, fuente primaria de etiqueta, fecha de revisión,
componentes con unidades y base por porción, y cualquier dato de nutrición de la
etiqueta. Datos desconocidos quedan vacíos. Revisar duplicados por marca, nombre,
presentación y versión de etiqueta; retirar una ficha si la fuente deja de respaldarla.
Priorizar omega 3, citrato de magnesio, citrato de potasio, vitamina D3,
multivitamínicos y sodio como cola de investigación, no como fichas aprobadas.
Una ficha pasa de candidata a publicada solo tras revisión de identidad, evidencia,
licencia de uso y consistencia de unidades. Los suplementos nunca alimentan los
totales nutricionales de comidas o minutas.

Referencias iniciales para investigar familias, sin atribuirles dosis de producto:

| Familia | Referencia general | Pendiente para ficha de marca |
| --- | --- | --- |
| Omega 3 | [NIH ODS](https://ods.od.nih.gov/factsheets/Omega3FattyAcids-Consumer/) | Fuente del aceite y EPA/DHA por porción de etiqueta |
| Citrato de magnesio | [NIH ODS](https://ods.od.nih.gov/factsheets/Magnesium-Consumer/) | Magnesio elemental por porción y forma declarada |
| Citrato de potasio | [NIH ODS](https://ods.od.nih.gov/factsheets/Potassium-Consumer/) | Potasio elemental por porción y forma declarada |
| Vitamina D3 | [NIH ODS](https://ods.od.nih.gov/factsheets/VitaminD-Consumer/) | D3 por porción y origen declarado por fabricante |
| Multivitamínicos | [NIH ODS](https://ods.od.nih.gov/factsheets/MVMS-Consumer/) | Lista completa y cantidades por porción de cada fórmula |
| Sodio / electrolitos | [NIH ODS](https://ods.od.nih.gov/News/odsdigest20260702/) | Producto exacto, forma y sodio por porción de etiqueta |

Suplementos are a Pro-only personal library. They are informational and never
contribute to nutritional totals. A DailyPlan can contain ordered supplement
intakes alongside meals; each intake has an optional time and one or more
supplements with planned quantities. Intake labels are derived from order.

Users can also save named intake compositions inside the Supplements area.
These presets contain ordered supplement doses but no time. After selecting a
preset while editing a DailyPlan, the user configures the time for that plan
instance and the system copies the composition into a new plan intake. Later
edits or deletion of the preset do not modify DailyPlans that already used it.

An intake's detail lists its supplements. Each supplement opens its own detail
with optional components, description, user-provided information and label
nutrition per default dose. Label nutrition is stored only on the library
supplement: it is not copied into intake snapshots and never contributes to
meal or DailyPlan nutritional totals. A plan containing only supplement
intakes is complete.

Completion is recorded per intake and lived day, using the same whole-item
criterion as meals. Meal and supplement panels and completion summaries are
mutually exclusive in the UI. Non-Pro users retain their data, but supplement
buttons open the Pro upsell and do not expose the stored content.

Rollout is controlled by `SUPPLEMENTS_FEATURE_ENABLED`, disabled by default.
Enabling it exposes the capability only to Pro users. Turning it off again
closes API and mobile access without changing stored records. Both migrations
can be applied and reversed on a disposable database, but reversing the model
migration after real users create supplements would delete their data. For a
deployed rollback, turn off the switch and keep the tables.

Supported use units: capsule, tablet, softgel, gummy, sachet, scoop, drop, ml,
g, mg, mcg, IU, and teaspoon. Components are optional informational lines in g,
mg, mcg, ml, or IU.
The separate form field uses capsule, tablet, softgel, gummy, sachet, powder,
liquid, or drop; it never determines nutrition or converts a dose automatically.
The same physical product may be entered separately as Food and Supplement;
this version does not link or synchronize those entries.

Unit choices are based on common oral supplement forms and label conventions
described by the [FDA](https://www.fda.gov/consumers/consumer-updates/fda-101-dietary-supplements)
and [NIH ODS](https://ods.od.nih.gov/HealthInformation/ODS_Frequently_Asked_Questions.aspx).
No conversion between units or medical benefit claim is inferred by the app.
