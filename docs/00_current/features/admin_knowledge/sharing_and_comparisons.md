# Compartir, Inbox y comparaciones

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de producto, soporte, operaciones y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Guía humana. Los permisos, expiraciones y contratos efectivos deben comprobarse en sharing,
> Inbox y comparators vigentes.

## Compartir sin entregar el objeto privado

My Scoope comparte una copia portable y versionada, no acceso al objeto privado original. El flujo
separa responsabilidades:

```text
entidad propia
  -> snapshot compartible
  -> preview de solo lectura
  -> claim explícito
  -> Inbox del receptor
  -> copia propia al guardar
```

Abrir un enlace no guarda ni acepta contenido. El receptor debe autenticarse cuando corresponda y
confirmar. Las invitaciones dirigidas por email añaden verificación de identidad; poseer el enlace no
reemplaza esa comprobación. Si el origen cambia después, el snapshot compartido conserva la versión
que recibió el usuario.

## Inbox

Inbox conserva elementos reclamados y permite marcarlos, descartarlos o guardarlos. Guardar crea una
copia independiente en la biblioteca del receptor. Revocar el enlace público impide nuevas
interacciones, pero no borra automáticamente una copia ya guardada por otra persona.

## Comparaciones

Foods, Meals y DailyPlans pueden compararse; Programs no forman parte del alcance actual. En Foods
se puede variar la cantidad usando la unidad configurada `g` o `ml`, y repetir el mismo alimento en
dos posiciones para comparar porciones. Meals y DailyPlans se comparan como entidades completas.

Una comparación guardada mantiene dos ideas:

- la selección editable de entidades y cantidades;
- un snapshot de nombres y valores calculados al guardar.

Por eso una comparación guardada puede no cambiar cuando se edita después un alimento o plan. Entrar
en edición y volver a guardar actualiza conscientemente su snapshot.

## Diagnóstico humano

| Pregunta | Explicación probable |
| --- | --- |
| “Compartí algo y luego lo edité, pero el receptor ve lo anterior” | El share conserva un snapshot histórico. |
| “Abrí el link pero no está en mi biblioteca” | Preview, claim y guardar son acciones separadas. |
| “El contenido guardado aparece duplicado” | La copia del receptor tiene ownership independiente. |
| “La comparación no refleja valores nuevos” | Puede estar mostrando el snapshot guardado. |
| “No puedo comparar programas” | Programs está fuera del alcance vigente del comparador. |

## Referencias

- [Evolución del producto](project_evolution.md)
- [Recorrido móvil](mobile_journey.md)
