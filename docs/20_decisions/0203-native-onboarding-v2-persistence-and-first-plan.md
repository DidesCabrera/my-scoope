# 0203 — Onboarding Native v2 persistente y primer plan diario

Status: accepted
Date: 2026-10-05

## Contexto

El storyboard Native aprobado incorpora objetivo, actividad habitual, frecuencia de
entrenamiento, preferencias alimentarias, una estimación explicable y la revisión de
un primer Plan diario. El onboarding productivo anterior solo persistía fecha de
nacimiento, sexo, altura y peso, y no podía reanudar el recorrido ni generar el plan.

Varios datos ya tienen autoridades establecidas. Duplicarlos en un payload propio de
onboarding produciría divergencias con Profile, Body Metrics, preferencias y el
NutritionSubjectContext.

## Decisión

- `Profile` conserva `nutrition_goal`, `activity_level`, `training_frequency`, la
  etapa reanudable y la propuesta de primer plan asociada.
- `WeightLog` sigue siendo la única autoridad del peso; el onboarding actualiza el
  registro del día mediante el servicio de Body Metrics.
- `NutritionPreferenceProfile` conserva patrón alimentario, alergias/intolerancias y
  alimentos evitados. El onboarding no crea un segundo modelo de preferencias.
- `activity_level` participa en la estimación de mantenimiento existente.
  `training_frequency` se persiste como contexto y no modifica TDEE, evitando doble
  conteo con la actividad habitual.
- El resumen usa el Target Estimator existente. La generación crea una propuesta
  revisable con el generador determinístico y solo la aprobación explícita aplica el
  Plan diario a la biblioteca.
- El onboarding solo se marca completo después de aplicar el primer plan y llegar a
  la elección comercial. Free continúa siendo una salida válida.
- La primera entrega funcional conecta Native y mantiene el endpoint v1 para
  compatibilidad con Web. La normalización visual/productiva de Web queda como una
  etapa posterior del mismo ciclo.

## Consecuencias

- Assistant y Solver pueden reutilizar actividad y frecuencia persistidas sin volver
  a pedirlas cuando están disponibles.
- Cerrar y abrir la app reanuda desde resumen, revisión del plan o elección comercial.
- Disclosures continúa antes de la ficha nutricional y Home.
- La propuesta fuente usada internamente para generar el plan queda cancelada y el
  plan concreto es el único artefacto revisable del recorrido.
- La disponibilidad de alimentos habilitados para Solver es una precondición
  operativa para generar el primer plan; los errores permanecen explícitos y no
  completan el onboarding silenciosamente.

## Razones y alternativas consideradas

| Decisión | Por qué | Alternativa descartada |
|---|---|---|
| Extender `Profile` con objetivo, actividad y frecuencia | Son atributos estables de la persona y ya forman parte del contexto nutricional reutilizable. | Guardarlos únicamente dentro de una sesión o un JSON de onboarding, porque obligaría a volver a preguntarlos y crearía dos versiones del perfil. |
| Mantener el peso en `WeightLog` | El peso es una métrica temporal; el servicio existente actualiza el registro del día y conserva su historia. | Agregar `weight_kg` a `Profile`, porque perdería fecha, procedencia e historial. |
| Reutilizar `NutritionPreferenceProfile` | Es la autoridad existente para preferencias aprobadas disponibles en distintos chats y propuestas. | Crear una tabla o payload exclusivo del onboarding, porque las restricciones podrían divergir al modificarse posteriormente. |
| Persistir `training_frequency` sin alterar TDEE | Es información útil para planificación futura, pero `activity_level` ya representa el multiplicador de actividad del estimador. | Sumar un ajuste energético por entrenamiento sin una regla validada, porque contaría movimiento dos veces. |
| Guardar el identificador de la propuesta, no una relación ORM | Permite reanudar el flujo y resolver la propuesta verificando propietario, sin acoplar el dominio Identidad al dominio Propuestas. | Un `ForeignKey` desde `Profile`, descartado por la política de fronteras de dominio y por aumentar el acoplamiento. |
| Generar una propuesta antes de crear el Plan diario | Preserva el contrato de control humano: la persona revisa y confirma antes de aplicar. | Crear el Plan directamente al tocar “Generar”, porque convertiría una estimación no revisada en una entidad final. |
| Completar el onboarding después de aplicar el plan | Evita mostrar un onboarding terminado cuando todavía no existe el resultado prometido. | Marcarlo completo al guardar la ficha o generar la propuesta, porque una interrupción dejaría un estado incoherente. |
| Separar rutas, esquemas, selectores, tipos y pruebas de onboarding | Mantiene los límites de tamaño y propiedad del repositorio y facilita evolucionar el flujo sin convertir Identidad en un módulo monolítico. | Seguir creciendo `identity.py`, `selectors.py` y `types.ts`, opción rechazada por los controles de deuda arquitectónica. |
| Implementar primero Native y mantener v1 para Web | El diseño aprobado y revisado vive en la UI Gallery Native; conservar v1 evita romper usuarios Web mientras se normaliza esa plataforma. | Reemplazar simultáneamente Web sin una revisión visual equivalente del flujo productivo. |

## Flujo y autoridad de estado

```text
intro
  -> disclosures versionados
  -> profile (captura local)
  -> summary (datos persistidos + estimación)
  -> plan (propuesta generada y revisable)
  -> plans (Plan diario aplicado)
  -> completed (Free o continuación a suscripción)
```

La UI no calcula calorías ni macros. `accounts.services.onboarding` coordina las
autoridades existentes y `mobile_api.routes.onboarding` solo valida scopes, payloads
y respuestas. El identificador persistido de propuesta siempre se resuelve junto al
usuario propietario antes de leerlo, aprobarlo o aplicarlo.

## Pendientes

### Para cerrar la primera versión Native

- ejecutar la migración `0067_profile_onboarding_v2` en staging;
- comprobar que staging tenga suficientes alimentos visibles y
  `solver_enabled=True` para generar un plan factible;
- realizar un smoke test con cuenta nueva: login, swipe, disclosures, ficha,
  generación, aplicación, Free y llegada a Home;
- revisar en dispositivo físico el teclado, scroll, targets táctiles, VoiceOver y el
  gesto de swipe;
- verificar reanudación cerrando la app en `summary`, `plan` y `plans`;
- definir mensajes de producto más específicos para indisponibilidad o inviabilidad
  del Solver;
- confirmar la experiencia comercial de Basic/Pro: actualmente conduce a la vista
  de suscripción, donde se concreta la compra.

### Para normalizar Web

- llevar la secuencia aprobada al onboarding Web productivo reutilizando los mismos
  servicios v2;
- sustituir el submit único v1 por el estado reanudable sin duplicar formularios ni
  cálculos;
- alinear Disclosures, preferencias, resumen, revisión del Plan diario y selección
  comercial con Native;
- retirar el endpoint v1 solo cuando Web y consumidores compatibles hayan migrado y
  exista evidencia de que ya no se usa.

### Evolución posterior

- decidir, con una regla nutricional probada, si `training_frequency` debe influir en
  planificación, distribución o recomendaciones sin modificar incorrectamente TDEE;
- permitir edición posterior de objetivo, actividad, frecuencia y preferencias desde
  “Mi cuenta” usando las mismas autoridades;
- evaluar guardado incremental de los pasos anteriores a `analyze`; hoy la ficha se
  persiste al solicitar el análisis y, si se cierra antes, se reinicia desde objetivo;
- decidir si el plan generado debe calendarizarse o fijarse en Home automáticamente;
  esta versión lo crea en la biblioteca y no inventa una calendarización;
- agregar analítica de abandono y éxito por etapa antes de optimizar o combinar
  pantallas introductorias.

## Referencias

- `docs/20_decisions/0202-onboarding-storyboard-and-cross-platform-flow.md`
- `docs/20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md`
- `docs/10_active_cycles/onboarding_flow_normalization_cycle.md`
- `accounts/services/onboarding.py`
- `mobile_api/routes/onboarding.py`
- `notas/application/nutrition_engine/target_estimator.py`
