# Ruta de preparación para los 62 alimentos reservados

Fecha de corte: 2026-11-11. Autoridad: catálogo publicado `2026.11.2`, lote de enriquecimiento `be50ac70-4d9b-491b-b135-d1077750d4ee`. Fuente de trabajo: `solver_219_first_pass_v1.csv`. La tabla operativa fila por fila es `solver_62_preparation_route_v1.csv` (clave estable `catalog_ref` y `source_record_id`). Esta ruta es una cola de revisión; no habilita ninguno de los 62 como candidato directo.

## Resultado y orden de trabajo

| Ruta | Filas | Decisión y siguiente trabajo |
| --- | ---: | --- |
| Contraparte preparada ya publicada | 23 | Existe un alimento preparado con nombre correspondiente entre los 157 elegibles. Revisar identidad y vincular solo si hace falta conversión de ingrediente crudo a porción cocida; no sumar el crudo al solver. |
| Posible alimento preparado en USDA SR Legacy | 21 | Se localizó un FDC ID preparado en el archivo oficial. Curar un alimento preparado separado tras comprobar especie, corte, método, base comestible, porción, alergias y rendimiento. Los 21 registros tienen energía, proteínas, grasas y carbohidratos reportados; esto no equivale a aprobación del alimento. |
| Sin equivalente preparado en SR Legacy | 8 | Buscar otra fuente primaria con licencia y base nutricional claras, o definir preparación/receta medible. No imputar valores cocidos desde el registro crudo. |
| Componente de receta | 10 | Vincular a una receta con cantidades y rendimiento verificados; permanecer fuera de la selección directa. |

Los ocho sin equivalente preparado en este archivo son hongo ostra, yuca, panceta de cerdo, anchoa, champiñón crimini, shiitake seco, hongo morchella y lenteja roja seca. Esta ausencia se limita al archivo USDA SR Legacy 2018; no demuestra que no exista otra fuente válida. La única alternativa localizada para calamar en el archivo es **frita** (FDC 171982): requiere receta o perfil de cocción específico y no debe representarse como calamar cocido genérico.

## Criterio de activación

1. Mantener el registro original de ingrediente, la fuente y el estado de preparación sin alterar los valores nutricionales crudos.
2. Para un alimento preparado nuevo, verificar identidad exacta, unidad por 100 g de parte comestible, nutrientes exigidos por el contrato, fuente/licencia, porción, límites, alérgenos positivos y etiquetas dietarias; registrar toda transformación o rendimiento. Si la fuente no representa la preparación consumida, conservarlo en revisión.
3. Publicar un lote versionado y reversible. Confirmar en catálogo autoridad, réplica operativa y consulta real del solver; comprobar idempotencia y que ningún ingrediente crudo o componente de receta se habilite por accidente.
4. Revisar los casos de mayor uso real antes de ampliar el catálogo. El orden interno de los 21 candidatos queda abierto a evidencia de uso y preparación concreta; no inventar prioridades nutricionales a partir de nombres.

## Evidencia de fuente

Los FDC ID originales y las 21 alternativas propuestas se contrastaron con el archivo oficial **USDA FoodData Central SR Legacy, JSON 2018-04**, SHA-256 `0fe8ae486a2c8eb42cb96413f058deb51863a46c8fb45006dd338ef`. La verificación del lote original confirmó 189/189 IDs USDA, 528/528 medidas y 1299/1299 nutrientes presentes sin diferencias. La fuente y su documentación están en https://fdc.nal.usda.gov/download-datasets/ y https://fdc.nal.usda.gov/data-documentation/ . Los FDC ID propuestos en la tabla enlazan directamente a la ficha de cada alimento. Los registros con `core-natural` requieren además comprobar la relación de identidad con su fuente interna antes de automatizar conversiones.
