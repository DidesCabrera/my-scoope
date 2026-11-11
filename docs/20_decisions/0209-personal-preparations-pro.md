# 0209 — Preparaciones personales como librería Pro

Status: accepted
Date: 2026-11-11

## Contexto

La decisión 0207 introdujo Preparaciones curadas como componentes de Comida y reservó la autoría personal para una etapa posterior. El modelo operacional ya tiene propietario, versiones inmutables y relaciones con Comidas. Felipe decidió ofrecer también a usuarios Pro el registro de sus propias Preparaciones, con una sección propia en la librería y un control oficial de disponibilidad como el de Suplementos.

## Decisión

La autoría personal se implementa en la autoridad operacional del usuario, separada del Food Catalog editorial. `PERSONAL_PREPARATIONS_FEATURE_ENABLED` controla la disponibilidad general y `can_use_personal_preparations` controla el acceso comercial Pro. La app presenta «Mis Preparaciones» con cards solo de las propias; el selector de Comidas incluye las globales y las personales accesibles.

Cada preparación personal se calcula desde alimentos operacionales accesibles al usuario, con cantidades en gramos, rendimiento final y porción doméstica. Cada edición crea una versión nueva, refresca las Comidas vivas y conserva los snapshots calendarizados. El retiro es lógico y preserva las versiones usadas. Los alérgenos no se infieren desde `notas.Food`, que actualmente no lleva un campo operacional de evaluación de alérgenos; se muestran como no evaluados.

## Consecuencias

La función requiere control en servidor y móvil, actualización del plan Pro existente, y pruebas de propiedad, apagado, cálculo, versiones y conservación histórica. La publicación editorial y su release siguen exclusivos del catálogo central. No se habilitan preparaciones anidadas ni autoría web en esta versión.
