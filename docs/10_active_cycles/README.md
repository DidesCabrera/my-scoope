# 10 Active Cycles

Esta carpeta contiene planes de ciclos futuros, activos, pausados, completados o superados que no deben confundirse con contratos vigentes de implementación.

Su objetivo es permitir que My Scoope conserve una **memoria estratégica accionable** sin mezclarla con los contratos actuales de arquitectura, features o decisiones ya aceptadas.

## Cuándo usar esta carpeta

Usar `docs/10_active_cycles/` para:

- planificar ciclos de patches próximos;
- ordenar prioridades entre proyectos grandes;
- definir métricas, objetivos y alcance antes de escribir código;
- preparar decisiones que más adelante pasarán a `docs/20_decisions/`;
- conservar contexto estratégico para futuras conversaciones con IA.

## Qué no debe vivir aquí

No usar esta carpeta como reemplazo de:

- `docs/00_current/`, que sigue siendo la fuente de verdad vigente para implementar;
- `docs/20_decisions/`, que registra decisiones aceptadas o historia técnica;
- `docs/90_archive/`, que conserva documentos superados o bitácoras históricas;
- `manual_docs/`, que contiene notas personales fuera de la documentación oficial.

## Estado de los documentos

Cada plan debe declarar un estado explícito:

```text
Status: planned / active / paused / completed / superseded
```

Cuando un ciclo planificado empiece a implementarse, el documento puede permanecer aquí como plan operacional, pero las decisiones estables que surjan deben registrarse también en `docs/20_decisions/`.

## En curso o pendientes de validación
- `mobile_api_domain_decomposition_cycle.md`: ciclo activo MADD00-MADD07 para
  convertir la propiedad lógica del API móvil en módulos físicos por dominio.
  Comparisons ya es el patrón de referencia con rutas, schemas y pruebas separadas,
  OpenAPI idéntico y presupuestos reducidos; siguen Propuestas, Calendarización,
  Librerías/Composición, Cuenta/Billing y Assistant.
- `consumer_mobile_enrichment_cycle.md`: ciclo MCE00-MCE08 completado en repositorio para una
  jornada intensiva que incorpora en la app React Native la gestión completa de la
  calendarización, el centro de propuestas, el comparador y el chat IA durable. El
  orden instala primero las superficies confiables y después conecta cards/acciones
  del Assistant, cerrando con recorridos integrados y evidencia de contrato. MCE00 y
  MCE01 están completados con baseline verde, catálogo de navegación seguro,
  contratos compartidos, estados de pantalla y polling durable. MCE02 también está
  completado con activación nativa, calendario, detalle diario, historial y ciclo de
  vida de `Mi programa`. MCE03 está completado con centro móvil de propuestas,
  revisión/aprobación separada de la aplicación, advertencia de sujeto externo y
  navegación al resultado. MCE04 también está completado con comparación
  autoritativa de Foods, Meals y DailyPlans, snapshots históricos guardados,
  edición explícita y navegación nativa. MCE05 está completado con historial de
  chats owner-scoped, conversación nueva/reanudada, turnos durables recuperables y
  bloqueo de doble envío. MCE06 está completado con objetos tipados, navegación
  contextual y acciones preparadas con confirmación confiable. MCE07 está
  completado con recorridos integrados, contexto tipado de comparaciones,
  refresco al volver y resiliencia. MCE08 cerró OpenAPI, 366 pruebas focalizadas,
  el fast gate de 95 pruebas, 1.770 pruebas Django completas, 24 pruebas móviles y
  35 rutas Expo. Sólo permanece como gate externo el smoke físico en iPhone.
- `catalog_enrichment_cycle.md`: CE01–CE10 implementa enriquecimiento asistido por Codex, por campo, gobernado y reversible, con clasificación multidimensional de capacidades. Las ejecuciones con datos reales en staging y producción permanecen como gates operacionales.
- `consumer_mobile_launch_cycle.md`: ciclo activo CML00-CML08. Reorienta el primer
  cliente móvil hacia consumidores que siguen su propio programa; separa seguridad,
  API, React Native, calendarización ejecutable, OCR de etiquetas, IAP y review de
  App Store en patches con evidencia independiente. CML00 está completado y CML01
  está completado en repositorio; restauración real, aplicación segura del Blueprint
  en staging y aprobación contable/legal siguen como gates externos. CML02 es el
  contrato API consumer-first y está completado en repositorio. CML03 también
  está completado en repositorio con Expo, sesión segura y recorrido nativo; su
  prueba física depende de Xcode y OAuth staging. CML04 está completado en
  repositorio con ejecución inmutable, adherencia, mediciones contextualizadas,
  revisiones, ajustes futuros auditados y coordinación de recordatorios. CML05
  está completado en repositorio con cámara, OCR local Apple Vision, revisión
  explícita y creación idempotente de alimentos privados; su gate físico depende
  de Xcode/dispositivo. CML06 está completado en repositorio con compra/restauración
  StoreKit verificada, conciliación Apple y agregación determinística con Mercado
  Pago; el ciclo sandbox físico sigue como gate externo. CML07 está completado en
  repositorio con Apple dentro del mismo PKCE, entrega APNs/local exclusiva,
  Keychain, manifiesto de privacidad y errores móviles sanitizados. Su gate físico
  exige macOS Tahoe 26.2+, Xcode 26.4, credenciales Apple y un iPhone. CML08 es el
  siguiente patch de TestFlight, metadata y preparación de review.
- `production_architecture_remediation_cycle.md`: ciclo activo PAR00-PAR10. PAR01-PAR05
  cierran en repositorio el arranque fail-closed con PostgreSQL, la topología Render
  versionada, CI completo sobre PostgreSQL, runbooks de recuperación y defaults de
  lanzamiento. PAR06-PAR10 separan la convergencia de modelos, el runtime AI asíncrono
  y la deuda estructural en releases con rollback propio.
- `billing_payments_tax_documents_cycle.md`: ciclo activo BILL00-BILL09. Mercado Pago
  será el primer recaudador y OpenFactura el emisor tributario, con fronteras separadas,
  verificación server-to-server, inbox/outbox idempotentes y proyección controlada hacia
  `accounts`. BILL00-BILL09 están implementados en repositorio; checkout, webhook y
  emisión real siguen desactivados hasta completar sandbox y aprobación contable.
- `project_control_clarity_foresight_cycle.md`: ciclo PCF00-PCF10 completado localmente
  y pendiente de validación en staging; crea
  una capa de control transversal basada en evidencia: CI alineado con staging,
  contrato y diagnóstico de ambientes, estado ejecutable, control plane read-only,
  registros documentales y de transiciones, portafolio de apuestas e interfaz de
  contexto para AI. Aporta contexto y feedback para decidir sin imponer un camino
  rígido. El cierre local aprobó la suite completa vigente en ese ciclo.
- `generic_food_coverage_cycle.md`: ciclo activo GFC00-GFC10 para derivar, mapear,
  importar y medir una cobertura ambiciosa de verduras, frutas, carnes/pescados,
  legumbres y lácteos genéricos relevantes para Chile. El manifiesto versionado es
  un mapa de cobertura, no una whitelist; su conteo final emerge de la enumeración
  y admite descubrimientos útiles bajo las mismas reglas de evidencia y revisión.
- `program_calendarization_notifications_cycle.md`: ciclo activo CAL00-CAL08 con
  implementación repository-side completa para activar programas sobre fechas reales,
  snapshots diarios, recordatorios diarios/por comida y Web Push idempotente. Quedan
  como gate externo las credenciales, scheduler y smoke real en staging.
- `food_catalog_growth_cycle.md`: ciclo activo FCG00-FCG10 con implementación completa y
  validación de datos reales en staging pendiente, para poblar efectivamente
  `CatalogFood` desde fuentes persistibles trazables, aprender su operación desde Admin
  Operations y validar muestras pequeñas antes de escalar, manteniendo `notas.Food` como
  snapshot operacional y dejando FatSecret fuera del alcance.
- `nutrition_solver_optimization_v2_cycle.md`: ciclo activo NSO00-NSO10 para evolucionar el
  solver de porciones v2 hacia optimización conjunta, explicable y contractualmente integrada
  con capacidades curadas de Food Catalog mediante snapshots operacionales.
- `launch_readiness_operational_safety_cycle.md`: ciclo planificado LR00-LR07 para preparar My Scoope para staging/produccion con seguridad de cuenta, settings productivos, rate limiting, guardas de creditos AI, observabilidad, CI y checklist operacional, apoyandose en el dominio comercial ya cerrado por ACC.
- `export_cycle_aware_workspaces_cycle.md`: ciclo activo para mantener exports focalizados y conscientes del contexto de cada ciclo.

## Ciclos completados

- `code_quality_consolidation_cycle.md`: ciclo CQC00-CQC08 completado; alinea CI con
  `staging`, incorpora `mobile_api` a una cobertura por ramas de 78% con mínimo de
  75%, controla dependencias y hotspots mediante presupuestos ejecutables, reduce
  tests móviles frágiles, agrega límites de consultas y amplía tipado/complejidad sin
  cambiar el contrato público `/api/v1/`.
- `nutrition_panel_energy_metrics_cycle.md`: ciclo NPE00-NPE05 completado; separa
  kcal absolutas de `% kcal`, agrega composición calórica intrínseca P/C/G en una
  barra acumulada compartida y crea el tab responsive `Calorías` sin cambiar el
  significado contextual de Alloc.
- `uis10_selective_css_loading_cycle.md`: UIS10 completado; carga Programs CSS solo en sus páginas, separa week tabs y elimina una referencia JavaScript inexistente.
- `uis09_message_card_contract_cycle.md`: UIS09 completado; declara la familia message-card para Proposal, Inbox y AI Chat.
- `uis08_collection_shell_cycle.md`: UIS08 completado; comparte shell y empty state entre Foods, Meals, DailyPlans y Programs.
- `uis07_entity_heading_contract_cycle.md`: UIS07 completado; normaliza headings, indicadores y metadata de entidades, incluyendo Programs.
- `uis06_detail_section_contract_cycle.md`: UIS06 completado; normaliza encabezados de secciones internas de DailyPlan, Program, Program Week y propuestas enriquecidas.
- `uis05_entity_card_contract_cycle.md`: UIS05 completado; establece la anatomía neutral de cards para Food, Meal, DailyPlan, Program y Program Week.
- `uis04_shared_panel_adoption_cycle.md`: UIS04 completado; migra paneles y tabs al contrato neutral compartido, manteniendo aliases legacy.
- `uis03_shared_visual_language_cycle.md`: UIS03 completado; declara que Programs comparte las primitivas visuales de Foods, Meals y DailyPlans.
- `technical_debt_priority_closure_cycle.md`: TDG09-TDG14 completado; coordinación
  AI separada, imports AI→`notas` en cero, E2E autenticado determinista, CI sin
  duplicación y retiro reversible de los bridges del solver y `Profile.plan`.
- `technical_debt_guardrails_cycle.md`: TDG00-TDG08 completado; superficies de calidad
  reproducibles, límites arquitectónicos y de deuda frontend, descomposición por
  dominios en Admin Operations y seams del runtime IA, preservando Food Catalog como
  dominio operacional estratégico.
- `email_delivery_abuse_protection_cycle.md`: EAP00-EAP08 completado en repositorio;
  quedan como gates externos la configuración de Turnstile/Render Key Value, la
  auditoría del histórico de Resend y el smoke real en staging.
- `ai_assistant_system_capability_parity_cycle.md`: ASP00-ASP06 completado; catálogo
  único AI/MCP, lecturas de sistema, propuestas nutricionales, acciones preparadas,
  separación billing/staff y matriz ejecutable de capacidades.
- `ai_assistant_post_tool_followup_transport_cycle.md`: PT00-PT06 completado.
- `ai_assistant_behavioral_alignment_cycle.md`: BA00-BA07 completado.
- `ai_assistant_client_memory_profile_objects_cycle.md`: CM00-CM24 completado.
- `account_plans_credits_cycle.md`: ciclo completado ACC00-ACC07 para mover planes comerciales, suscripciones, créditos y entitlements hacia `accounts`, manteniendo tokens/costos como observabilidad interna y migrando gradualmente desde `notas.Plan` y créditos IA transicionales.
- `onboarding_nutrition_profile_cycle.md`: ciclo completado ONB00-ONB09 para onboarding nutricional mínimo: `accounts` conduce el flujo, `notas` persiste ficha personal y Body Metrics, `ai_assistant` decide sujeto nutricional y `nutrition_solver` calcula sobre `NutritionSubjectContext`, incluyendo warning cuando una propuesta externa se guarda en librería personal.
- `nutrition_solver_app_cycle.md`: ciclo completado para separar progresivamente el motor de optimización nutricional hacia una app Django `nutrition_solver`, con contratos puros, solver/validators extraídos, adapter operacional desde `notas.Food`, integración con AI Assistant y propuestas revisables. La UI directa se canceló/difirió por decisión estratégica.
- `food_catalog_launch_readiness_cycle.md`: ciclo completado para madurar la app existente `food_catalog` desde fundación técnica hacia capacidad operacional de lanzamiento: curación, seed natural, FatSecret, Open Food Facts, marcas y bridge solver-ready. FC-12 de métricas se difiere al ciclo transversal de Product Intelligence/Admin Analytics.
- `product_intelligence_admin_analytics_cycle.md`: ciclo completado ADM00-ADM10.6 para crear `admin_analytics` como dashboard estratégico staff-only, transversal y read-first, con overview ejecutivo, métricas de cuentas/créditos, AI Assistant, actividad nutricional, Food Catalog, Nutrition Solver, filtros, alertas internas, shell independiente y refinamientos mobile.
- `admin_operations_console_cycle.md`: ciclo completado OPS00-OPS08 para crear `admin_operations` como consola operacional staff-only, action-oriented y auditable, separada de `admin_analytics` y del Django Admin legacy/raw.

## Relación con CI y test hygiene

El ciclo CI00-CI05 ya está cerrado y documentado como QA/operación vigente en:

```text
docs/40_technical/qa/ci_stabilization_qa.md
docs/40_technical/operations/testing_and_ci_policy.md
docs/20_decisions/0080-ci-stabilization-and-test-hygiene.md
```

Los ciclos futuros deben considerar esta política antes de cambiar contratos, workflows, tests o settings de CI.

## Relación con arquitectura documental

La evolución de `docs/` queda regulada por:

```text
docs/00_current/AI_README.md
docs/00_current/PROJECT_STATE.md
docs/40_technical/operations/docs_information_architecture.md
docs/20_decisions/0082-docs-information-architecture-baseline.md
```

Un plan completado no debe quedar como fuente ambigua. Sus decisiones durables deben promoverse a `docs/00_current/` o registrarse en `docs/20_decisions/`.
