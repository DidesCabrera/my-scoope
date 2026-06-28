# AI Implementation Guide

Guía para que una IA implemente cambios en My Scoope sin romper patrones del sistema.

## Antes de modificar código

1. Leer `docs/README.md`.
2. Leer `docs/current/architecture/layers.md`.
3. Leer `docs/current/architecture/rules.md`.
4. Leer `docs/current/architecture/section_creation_guide.md`.
5. Revisar docs de feature si existen.

## Documentos de autoridad

Alta autoridad:

```text
docs/current/
docs/decisions/
```

Baja autoridad:

```text
docs/archive/
manual_docs/
```

`manual_docs/` no debe usarse para implementar.

## Reglas de código

- Mantener views delgadas.
- No poner lógica de negocio reusable en templates.
- No poner writes en presentation.
- No importar presentation/interface desde application.
- No crear CSS nuevo si existe patrón reutilizable.
- No dividir `domain/models.py` sin una tarea dedicada.
- Agregar tests cuando se toque parsing, payloads, commands o rutas críticas.

## AI nutricional y generación asistida

Para flujos de onboarding nutricional, generación de planes o asistentes internos, leer además:

```text
docs/current/features/ai_nutrition_onboarding/ai_nutrition_onboarding.md
docs/current/features/proposals.md
docs/current/features/food_catalog/food_catalog_app.md
```

Regla principal:

```text
La IA conversa. MyScoope calcula, valida y optimiza. El usuario revisa y aprueba.
```

La IA no debe crear entidades productivas directamente. Debe producir briefs, preguntas, explicaciones o propuestas revisables que pasen por validación de aplicación.

## Cuando haya duda

Buscar una sección similar vigente y seguir su estructura actual, no documentos archivados.
