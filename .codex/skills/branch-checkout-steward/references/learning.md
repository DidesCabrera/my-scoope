# Encargado de ramas y checkouts — aprendizaje inicial

Revisado: 2026-11-19. Rol definido por Felipe y registrado como `pilot`. El chat
[Encargado Ramas y Checkout](codex://threads/01a1b122-f792-72a0-945b-ba943851239b)
contiene trabajo previo útil, pero su título no demuestra que esta skill haya
estado activa antes de existir.

## Prácticas recuperadas

- **Comprobar remoto y local por separado.** `origin/staging` en caché puede ir
  atrasado. La auditoría debe consultar la cabeza remota y distinguir igualdad
  de SHA de distancia de commits calculada con objetos locales. Fuentes:
  `.codex/skills/parallel-work-coordinator/SKILL.md` y
  `.codex/skills/fresh-task-checkout/SKILL.md`.
- **Un checkout no es una rama prescindible.** Antes de retirar un detached o una
  rama sin upstream, verificar cambios sin commit, commits exclusivos,
  ascendencia de staging/main, PR, dueño y recuperación. En el chat previo Felipe
  solicitó retirar tres checkouts sin rama; fue una instrucción concreta, no una
  política general de borrar todos los detached.
- **Respetar el reporte acordado.** Felipe pidió una fila por rama y distinguió
  commits propios, cambios sin commit, checkout y commits detrás. Corrigió una
  respuesta que había cambiado ese formato; conservar preferencias explícitas
  del reporte vigente. Fuente: chat citado, revisión de ramas del 2026-11-19.
- **Las hipótesis necesitan verificación.** El mismo chat corrigió diagnósticos
  erróneos sobre proyectos visibles y permisos Git. No atribuir bloqueos a una
  configuración, modelo o cambio de proyecto antes de comprobar la operación
  fallida. El reintento con autorización específica quedó en `AGENTS.md`; su
  existencia no prueba que haya sido la causa de un fallo previo.
- **Separar funciones.** Parallel Work Coordinator audita simultaneidad y Metro
  en modo lectura; `fresh-task-checkout` prepara un inicio actualizado y
  `publish-to-staging` integra contenido probado. Este rol decide y documenta el
  ciclo completo de ramas y checkouts a petición de Felipe, sin sustituir esos
  contratos.

## Primera evaluación

Un inventario real debe permitir a Felipe identificar sin ambigüedad qué rama
contiene cada trabajo, qué está integrado, qué está atrasado, qué checkout está
ocupado y qué limpieza es segura. Una transición posterior debe preservar el
trabajo ajeno y dejar prueba del estado final.
