# Current Docs

Esta carpeta contiene documentación vigente. Una IA o desarrollador debe preferir estos documentos sobre cualquier archivo en `docs/archive/`.

## Lectura recomendada

1. `architecture/layers.md`
2. `architecture/rules.md`
3. `design/ui_system.md`
4. `architecture/section_creation_guide.md`
5. `architecture/ui_patterns.md`
6. `architecture/component_inventory.md`
7. `architecture/ai_implementation_guide.md`
8. `features/food_catalog.md`
9. `features/ai_assistant/README.md`
10. `../decisions/0020-ai-assistant-django-app-and-chat-engine.md`
11. `../decisions/0028-ai-assistant-activation-cycle.md`
12. `features/ai_nutrition_onboarding/ai_nutrition_onboarding.md`
13. `../decisions/0050-onboarding-nutrition-profile-and-subject-context.md` cuando el trabajo toque onboarding nutricional, ficha personal, sujeto de cálculo o PPK en propuestas externas.
14. `../planning/onboarding_nutrition_profile_cycle.md` para historia y alcance cerrado del ciclo ONB00-ONB09.
15. `qa/onboarding_nutrition_v1_qa.md` cuando se modifique onboarding, ficha nutricional, subject context, solver o warning de propuestas externas.
16. `architecture/nutrition_solver_extraction_map.md` cuando el trabajo sea Nutrition Solver.
17. `../planning/README.md` cuando el trabajo sea planificación de ciclos futuros.

## Criterio

Si un documento en `current/` contradice un documento en `archive/`, gana `current/`.

## UI System

`design/ui_system.md` es el contrato vigente para CSS, componentes visuales, tokens, z-index, breakpoints y criterios de crecimiento de UI. Debe consultarse antes de crear nuevos estilos o componentes.

## Relación con Planning Docs

`docs/planning/` puede orientar próximos ciclos, pero `docs/current/` sigue siendo la fuente de verdad para implementar comportamiento vigente. Si un plan se activa y define contratos estables, esos contratos deben moverse o reflejarse en `current/` y/o `decisions/`.
