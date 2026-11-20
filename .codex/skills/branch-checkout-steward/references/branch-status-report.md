# Formato acordado: estado de ramas y checkouts

Felipe confirmó esta tabla mediante captura el 2026-11-20. La última columna,
recortada en la captura, se llama **Detrás**: el chat
[Encargado Ramas y Checkout](codex://threads/01a1b122-f792-72a0-945b-ba943851239b)
la definió como commits detrás de `origin/staging` y la ubicó después de Checkout.
Los números de aquella captura pertenecen a un corte anterior; nunca se reutilizan
como estado actual.

## Tabla obligatoria

| Rama | Commits propios | Cambios sin commit | Por eliminar | Checkout | Detrás |
|---|---:|---:|:---:|:---:|---:|
| `ejemplo` | 🟢 0 | 🟢 0 | 🟢 | Sí | 3 |

Una fila por **rama local**, incluidas `main` y `staging`. Presenta los checkouts
sin rama en una nota o tabla separada. En la primera columna puede omitirse el
prefijo común `codex/` para legibilidad; indica esa convención y conserva completo
el resto del nombre. No sustituir columnas por un resumen narrativo ni cambiar su
orden cuando se solicite este reporte.

## Significado de cada columna

- **Commits propios:** commits alcanzables desde la rama y no desde el
  `origin/staging` remoto verificado. 🟢 `0`; 🔴 número mayor que cero. Un commit
  propio de `main` puede ser un merge de promoción; explícalo si importa, sin
  convertirlo automáticamente en trabajo pendiente.
- **Cambios sin commit:** número de rutas modificadas, preparadas o sin seguimiento
  en el checkout de esa rama, excluyendo archivos ignorados. 🟢 `0`; 🔴 número
  mayor que cero; `—` si no tiene checkout; `?` si no pudo inspeccionarse.
- **Por eliminar:** 🟢 significa **candidata técnica**: cero commits propios,
  cero cambios sin commit y ninguna reserva o dependencia conocida. 🔴 si hay
  trabajo propio o cambios sin commit. 🟡 si parece limpia, pero existe uso,
  reserva o evidencia insuficiente. `—` para `main` y `staging`. El color no
  autoriza borrar; antes de retirar hay que comprobar integración del contenido,
  dueño, procesos, PR, dependencias y recuperabilidad según el `SKILL.md`.
- **Checkout:** `Principal`, `Sí` o `Ninguno`; si falta evidencia, `?`.
- **Detrás:** número de commits alcanzables desde `origin/staging` y no desde la
  rama. Mostrar solo la cifra, sin icono. Calcula ambas distancias mediante
  `git rev-list --left-right --count origin/staging...<rama>` después de verificar
  el remoto. Si no se pudo comprobar la cabeza remota, marca la distancia como
  no verificada; no presentes una referencia local en caché como actual.

Encabeza el reporte con fecha y hora del corte, zona horaria y SHA abreviado de
`origin/staging`. Debajo de la tabla explica excepciones materiales: checkouts
sin rama, ramas reservadas, diferencia de historial frente a contenido, referencias
remotas no verificadas y cualquier dato que impida concluir que una rama puede
retirarse. No interpretes la imagen histórica como autorización para eliminar.
