# 00 Current Docs

Esta carpeta contiene documentación vigente y de alta autoridad. Una IA o desarrollador debe preferir estos documentos sobre cualquier archivo en `docs/90_archive/`.

## Lectura recomendada

1. `AI_README.md`
2. `PROJECT_STATE.md`
3. `../40_technical/operations/docs_information_architecture.md`
4. `architecture/layers.md`
5. `architecture/rules.md`
6. `design/ui_system.md`
7. `architecture/section_creation_guide.md`
8. `architecture/ui_patterns.md`
9. `architecture/component_inventory.md`
10. `architecture/ai_implementation_guide.md`
11. `features/food_catalog.md`
12. `features/ai_assistant/README.md`
13. `../20_decisions/0020-ai-assistant-django-app-and-chat-engine.md`
14. `../20_decisions/0028-ai-assistant-activation-cycle.md`
15. `features/ai_nutrition_onboarding/ai_nutrition_onboarding.md`
16. `../20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md` cuando el trabajo toque onboarding nutricional, ficha personal, sujeto de cálculo o PPK en propuestas externas.
17. `../10_active_cycles/onboarding_nutrition_profile_cycle.md` para historia y alcance cerrado del ciclo ONB00-ONB09.
18. `../40_technical/qa/onboarding_nutrition_v1_qa.md` cuando se modifique onboarding, ficha nutricional, subject context, solver o warning de propuestas externas.
19. `architecture/nutrition_solver_extraction_map.md` cuando el trabajo sea Nutrition Solver.
20. `features/admin_knowledge/README.md` como Knowledge Center para operación conjunta de Food
    Catalog, snapshots, Nutrition Solver, shadow mode y rollback.
21. `../40_technical/qa/ci_stabilization_qa.md` cuando el trabajo toque GitHub Actions, CI, tests desfasados o estabilización de `staging`.
22. `../40_technical/operations/testing_and_ci_policy.md` antes de abrir/reabrir PRs, cambiar workflows o ajustar tests.
23. `../40_technical/qa/testing_hygiene_guide.md` antes de crear, relajar o corregir tests después de bugs reales en staging/CI.
24. `../10_active_cycles/README.md` cuando el trabajo sea planificación de ciclos futuros.

## Criterio

Si un documento en `00_current/` contradice un documento en `90_archive/`, gana `00_current/`.

## UI System

`design/ui_system.md` es el contrato vigente para CSS, componentes visuales, tokens, z-index, breakpoints y criterios de crecimiento de UI. Debe consultarse antes de crear nuevos estilos o componentes.

## Relación con Planning Docs

`docs/10_active_cycles/` puede orientar próximos ciclos, pero `docs/00_current/` sigue siendo la fuente de verdad para implementar comportamiento vigente. Si un plan se activa y define contratos estables, esos contratos deben moverse o reflejarse en `00_current/` y/o `20_decisions/`.
