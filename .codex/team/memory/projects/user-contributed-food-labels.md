# Aportes voluntarios de etiquetas a Food Catalog

Status: proposed
Started: 2026-11-15
Sponsor: Felipe Dides
Owner role: `catalog-curation-steward`

## Desired outcome

Transformar etiquetas compartidas voluntariamente en candidatos revisables para Food Catalog sin publicar ni promover alimentos privados de forma automática.

## Scope and exclusions

El especialista de curación es dueño del inventario de la fuente, la rúbrica, la cola de excepciones, la evaluación del piloto y los lotes propuestos. El puente técnico entre la aplicación de consumo y la autoridad central requiere diseño y ejecución por Backend. Publicación y snapshots quedan fuera del intake automático.

## Current state

La fuente `FoodLabelCaptureReceipt` con payload confirmado e imagen de curación existe en el trabajo local de digitalización, pendiente de integración y despliegue. No hay evidencia de contribuciones reales ni intake hacia la autoridad central. Ver `.codex/team/areas/catalog-operations/source-registry.yaml` y el [plan del ciclo](../../../../docs/10_active_cycles/user_contributed_food_labels_cycle.md).

## Evidence and authoritative sources

- Contrato de captura: `docs/00_current/features/nutrition_label_capture.md` y código de `notas`/`mobile_api`.
- Autoridad y publicación: `docs/20_decisions/0199-central-food-catalog-authority-and-versioned-delivery.md` y `food_catalog`.
- Proyecto y criterios pendientes: `docs/10_active_cycles/user_contributed_food_labels_cycle.md`.

## Decisions and assumptions

- El usuario controla futuros envíos con un switch opt-in; apagarlo no retira aportes anteriores.
- El material compartido es evidencia candidata, no un alimento aprobado ni un permiso de publicación automática.
- El puente y la cola aún no existen; no inferir disponibilidad operacional a partir del código local.

## Next useful checkpoint

Tras integrar y desplegar la captura, levantar inventario de solo lectura y preparar rúbrica e intake gobernado para un lote piloto pequeño.

## Material updates

- 2026-11-15 — Fuente y proyecto registrados; conexión a Food Catalog todavía propuesta.
