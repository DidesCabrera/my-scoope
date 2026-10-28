# 00 Current Docs

Status: current
Date: 2026-10-28
Audience: developers and AI assistants

Esta carpeta contiene documentación vigente y de alta autoridad. Una IA o desarrollador debe preferir estos documentos sobre cualquier archivo en `docs/90_archive/`.

## Lectura recomendada

1. `AI_README.md`, comenzando por la bienvenida de Felipe Dides: una AI es también clienta y usuaria actual de My Scoope.
2. `PROJECT_STATE.md` para el mapa consolidado vigente.
3. `CONSUMER_PRODUCT_BRIEF.md` para entender a quién sirve el producto y el recorrido principal.
4. `PRODUCT_PORTFOLIO.md` cuando el trabajo implique prioridades, apuestas o próximos experimentos.
5. `../40_technical/operations/docs_information_architecture.md`
6. `architecture/layers.md`
7. `architecture/rules.md`
8. `features/calendarization.md` para la autoridad de planificación, Today y progreso.
9. `design/ui_system.md`
10. `design/mobile_visual_system.md` cuando el trabajo toque React Native o la traducción visual nativa.
11. `architecture/section_creation_guide.md`
12. `architecture/ui_patterns.md`
13. `architecture/component_inventory.md`
14. `architecture/ai_implementation_guide.md`
15. `features/food_catalog.md`
16. `features/ai_assistant/README.md`
17. `features/project_control.md` cuando el trabajo toque ambientes, CI, estado ejecutable, Admin Operations Project Control o contexto para AI.
18. `../20_decisions/0020-ai-assistant-django-app-and-chat-engine.md`
19. `../20_decisions/0028-ai-assistant-activation-cycle.md`
20. `features/ai_nutrition_onboarding/ai_nutrition_onboarding.md`
21. `../20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md` cuando el trabajo toque onboarding nutricional, ficha personal, sujeto de cálculo o PPK en propuestas externas.
22. `../10_active_cycles/onboarding_nutrition_profile_cycle.md` para historia y alcance cerrado del ciclo ONB00-ONB09.
23. `../40_technical/qa/onboarding_nutrition_v1_qa.md` cuando se modifique onboarding, ficha nutricional, subject context, solver o warning de propuestas externas.
24. `../20_decisions/0202-onboarding-storyboard-and-cross-platform-flow.md` y
    `../10_active_cycles/onboarding_flow_normalization_cycle.md` cuando se diseñe o
    normalice el flujo inicial, sus storyboards Web/Native, contenido, planes o la
    semántica de `training_frequency`.
25. `architecture/nutrition_solver_extraction_map.md` cuando el trabajo sea Nutrition Solver.
26. `../40_technical/qa/ci_stabilization_qa.md` cuando el trabajo toque GitHub Actions, CI, tests desfasados o estabilización de `staging`.
27. `../40_technical/operations/testing_and_ci_policy.md` antes de abrir/reabrir PRs, cambiar workflows o ajustar tests.
28. `../40_technical/qa/testing_hygiene_guide.md` antes de crear, relajar o corregir tests después de bugs reales en staging/CI.
29. `../10_active_cycles/README.md` cuando el trabajo sea planificación de ciclos futuros.
30. `features/calendarization.md` y
    `../40_technical/operations/calendarization_notifications_runbook.md` cuando el
    trabajo toque agenda, zona horaria, Web Push o el worker de notificaciones.
31. `features/billing.md`, `../10_active_cycles/billing_payments_tax_documents_cycle.md`
    y `../20_decisions/0154-billing-payment-tax-boundary.md` cuando el trabajo toque
    planes pagados, Mercado Pago, OpenFactura, webhooks, conciliación o DTE.
32. `features/mobile_composition_pickers.md` cuando el trabajo toque los flujos
    nativos de agregar/reemplazar Food, Meal o DailyPlan y sus proyecciones.
33. `features/sharing.md`, `features/inbox.md`, `features/comparators.md` y
    `../40_technical/operations/sharing_operations_runbook.md` cuando el trabajo
    toque enlaces compartidos, invitaciones, Inbox o su operación.
34. `features/beta_observability.md` y
    `../40_technical/operations/ios_release_capabilities_runbook.md` cuando el
    trabajo parta de crashes, errores beta, builds o señales de producción.

Cuando el repositorio está disponible, ejecutar primero `python manage.py
ai_project_context --json` ofrece una síntesis sanitizada de estado, decisiones,
ciclos, transiciones y apuestas. Es una entrada eficiente, no un sustituto de los
documentos específicos y el código relevante.

## Criterio

Si un documento en `00_current/` contradice un documento en `90_archive/`, gana `00_current/`.

## Excepción: proyección humana de Knowledge Center

`features/admin_knowledge/` alimenta exclusivamente la app humana Knowledge Center. Sus documentos
son explicativos y no normativos: no deben usarse para comprender el código, decidir arquitectura
ni implementar features. No se actualizan como parte de ciclos normales; solo cambian cuando Felipe
solicita explícitamente una actualización del Knowledge Center. La autoridad permanece en el código,
los tests, las decisiones y la documentación normativa aplicable.

## UI System

`design/ui_system.md` es el contrato vigente para CSS, componentes visuales, tokens, z-index, breakpoints y criterios de crecimiento de UI. Debe consultarse antes de crear nuevos estilos o componentes.

## Relación con Planning Docs

`docs/10_active_cycles/` puede orientar próximos ciclos, pero `docs/00_current/` sigue siendo la fuente de verdad para implementar comportamiento vigente. Si un plan se activa y define contratos estables, esos contratos deben moverse o reflejarse en `00_current/` y/o `20_decisions/`.
