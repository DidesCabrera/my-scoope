---
name: ci-timing-report
description: Present estimated and observed durations for My Scoope CI checks required to integrate a staging-to-main pull request. Use when Felipe asks how long the tests, validation, or PR gate will take.
---

# CI timing report

Give Felipe a recognizable table of the checks required for a `staging` to `main` PR. Its purpose is to make the expected wait and the slowest check visible for planning integration. The required validation tier comes from `docs/40_technical/operations/testing_and_ci_policy.md`; the workflow definition is `.github/workflows/django-ci.yml`.

## Report

- Label historical values **estimados** and identify their source run and date. If the user asks about a current PR, inspect its exact GitHub Actions run and report observed job durations and current conclusions instead.
- Use one row per CI job, with columns **Prueba o control**, **Tiempo estimado** (or **Duración observada**), and **Resultado** when reporting an actual run. Preserve the workflow's job names in understandable Spanish. Include the preflight and final summary so the complete wait is accounted for.
- Show the elapsed wall-clock time separately. Jobs run in parallel; do not sum their durations to calculate the total. Compute it from workflow start to completion. If still running, show elapsed time and mark pending jobs accordingly.
- State which job determines most of the wait. Do not describe job duration as the duration of each individual test case.

## Reference estimate

The following is a planning reference from [PR #152, run 43903132863](https://github.com/DidesCabrera/my-scoope/actions/runs/43903132863), completed on 2026-11-16. Refresh it when recent executions show a material change or the workflow changes.

| Prueba o control | Tiempo estimado |
|---|---:|
| Selección de pruebas y revisión previa | 9 s |
| Frontend: compilación y pruebas unitarias | 12 s |
| Django: controles estructurales rápidos | 1 min 7 s |
| Navegador: prueba básica | 2 min 36 s |
| App móvil: contrato y compilación | 2 min 18 s |
| MCP: contratos y protocolo | 25 s |
| Análisis estático y dependencias | 29 s |
| Django: regresión completa | 14 min 26 s |
| Django con PostgreSQL: regresión | 10 min 24 s |
| Resumen final | 6 s |

Elapsed workflow time in that run: **15 min 58 s**. All jobs succeeded. This is an observation for estimation, not a guaranteed future duration.
