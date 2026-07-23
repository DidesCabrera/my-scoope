# Food Catalog para Nutrition Solver

Status: human_reference
Date: 2026-07-17
Audience: usuarios staff humanos de curación, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Orientación exclusiva para personas. No define contratos de Food Catalog, no forma parte del
> contexto normativo de Codex y no se sincroniza automáticamente con ciclos o features.

## Objetivo operativo

Food Catalog aporta hechos nutricionales y funcionales auditables. El solver mejora cuando esos
hechos son precisos, versionados y llegan al snapshot operacional; no necesita ni debe consultar el
registro maestro en tiempo real.

## Capacidades que se curan

| Campo maestro | Impacto | Criterio operativo |
| --- | --- | --- |
| Macros por 100 g | Alto, nutricional | Valores consistentes con fuente y `data_quality_score`. |
| Porción default, mínima, máxima y paso | Alto, factibilidad | Unidades homogéneas, `min <= default <= max` y paso positivo. |
| `preparation_state` | Alto, seguridad semántica | Distinguir raw, cooked, dry, hydrated y ready-to-eat. |
| `functional_roles` | Alto, coherencia | Lista multirol; no forzar una categoría exclusiva. |
| `meal_affinities` | Medio, preferencia | breakfast, snack, main o dinner cuando exista evidencia culinaria. |
| `food_form` | Medio, gramática | ingredient, mixed_dish, beverage o condiment. |
| `dietary_tags` y `allergens` | Alto cuando se restrinja | Registrar sólo hechos sustentados; ausencia no equivale a “libre de”. |
| `preparation_effort` | Preferencia | unknown, none, low, medium o high. |
| `cost_band` | Preferencia | unknown, low, medium o high; no es un precio exacto. |
| `solver_feature_confidence` | Diagnóstico | Confianza 0–100 por capacidad, no una confianza global inventada. |
| `solver_capabilities_version` | Trazabilidad | Actualmente `solver_food_capabilities.v1`. |

Roles funcionales usados por la gramática actual:

```text
primary_protein
supporting_protein
starch_or_carbohydrate
mixed_food
vegetable
fruit
added_or_dense_fat
supporting_fat
```

Un alimento puede cubrir varios roles. Por ejemplo, una legumbre puede aportar proteína de apoyo y
carbohidrato; la gramática decide cómo participa en una combinación, no Food Catalog por sí solo.

## Checklist de solver readiness

Cuando `CatalogFood.solver_enabled=True`, el chequeo exige:

- `data_quality_score >= 70`;
- `food_group` presente;
- estado de preparación explícito;
- porción default;
- mínimo, máximo y paso explícitos o inferibles;
- orden válido de límites y paso positivo.

El chequeo genera warnings, sin inventar datos, cuando:

- el estado es raw o dry y el contexto comestible/cocido requiere mayor claridad;
- faltan roles funcionales y el adaptador deberá usar derivación identificada;
- faltan afinidades y el solver tendrá afinidad neutral.

`solver_enabled=False` no impide continuar la curación o publicación maestra, pero sí impide que el
alimento sea elegible como candidato operacional del optimizador.

## Publicación y snapshot

Publicar `CatalogFood` no lo convierte automáticamente en alimento del solver. El flujo correcto es:

```text
1. Curar y validar CatalogFood.
2. Publicar mediante el workflow protegido.
3. Ejecutar el protocolo explícito de snapshot.
4. Verificar notas.Food.solver_capabilities_version y solver_capabilities.
5. Verificar notas.Food activo, visible y solver_enabled.
6. Recién entonces el adaptador puede construir SolverFoodProfile.
```

El snapshot copia valores, confianza, fuente y versión. El solver recibe el ID operacional de
`notas.Food`; nunca recibe `catalog_ref`, IDs de proveedor ni payloads externos.

## Qué ocurre con datos ausentes

- Una capacidad opcional ausente permanece ausente y aparece en diagnóstico.
- Si faltan roles funcionales, el adaptador puede derivarlos desde macros con fuente
  `macro_role_rules.v1`, confianza reducida y marca `derived=True`.
- No se debe convertir ausencia de alérgenos o tags en una afirmación negativa.
- Volver a curar el maestro no cambia planes históricos ni snapshots existentes hasta republicar.

## Diagnóstico rápido

| Síntoma | Revisar primero | Corrección esperada |
| --- | --- | --- |
| Alimento no aparece | active, visibility, `solver_enabled` y snapshot | Corregir elegibilidad o republicar snapshot. |
| Comida nutricionalmente válida pero incoherente | roles, afinidades y forma | Curar capacidades y confianza; no cambiar macros para compensar. |
| Porciones imposibles o extrañas | unidad, default, min, max y step | Corregir bounds en catálogo y refrescar snapshot. |
| Raw/cooked mezclados | `preparation_state` y fuente nutricional | Separar registros/estados y publicar el correcto. |
| Cambio maestro no se refleja | versión/source del snapshot operativo | Ejecutar publicación/snapshot explícito y verificar trazabilidad. |
| Resultado externo aparece como candidato | frontera de importación/curación | Detener flujo: FatSecret/OFF no son `CatalogFood` ni `notas.Food`. |

## Inventario y calidad en Admin Operations

La pestaña staff-only `Admin Operations > Food Catalog > Inventario y calidad` consulta directamente
todos los registros persistidos en `CatalogFood`. Es una vista de observabilidad de sólo lectura; no
publica, materializa ni modifica alimentos.

La vista incluye:

- inventario paginado con todos los campos maestros, fuentes/evidencia, porciones y aliases;
- búsqueda y filtros por estado, fuente, grupo alimentario y habilitación del solver;
- cobertura por familias normalizadas de `food_group`, incluyendo verduras y proteínas;
- distribución por origen, publicación y calidad promedio;
- promedios descriptivos de macros y fibra por 100 g;
- brechas explícitas: grupo ausente, evidencia ausente, nutrición extendida incompleta y semántica
  culinaria desconocida.

Las familias del reporte homologan únicamente aliases conocidos de `food_group`. Los valores vacíos
o no reconocidos permanecen visibles como `Sin taxonomía estándar`; nunca se infiere la categoría
desde el nombre del alimento. Los promedios nutricionales describen la composición del inventario,
no constituyen metas dietarias ni ponderan el uso real de cada alimento.

## Referencias

- [Knowledge Center](README.md)
- [Nutrition Solver](nutrition_solver.md)
- [Food Catalog vigente](../food_catalog.md)
- [ADR 0142: capacidades curadas](../../../20_decisions/0142-food-catalog-curated-solver-capabilities.md)
- [ADR 0143: snapshot operacional](../../../20_decisions/0143-operational-solver-capability-snapshot.md)
