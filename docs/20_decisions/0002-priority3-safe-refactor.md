# 0002 - Priority 3 Safe Refactor

Status: accepted

This note documents the scope chosen for the Priority 3 maintainability pass.

## Applied now

### URL modules

`notas/urls.py` is now a thin aggregator. Feature routes live under:

```text
notas/interface/urls/
```

This keeps URL growth localized by feature and makes future AI-assisted changes safer because a task touching Programs, Comparators, Inbox, Foods, Meals or DailyPlans can inspect a smaller routing file.

### Program view cleanup

`notas/interface/views/programs.py` was reduced by removing dead/duplicated chart, KPI, grid and card builder helpers that already live in `notas/presentation/viewmodels/programs.py`.

Program action/header/viewmodel assembly helpers now live in:

```text
notas/presentation/viewmodels/program_actions.py
```

This leaves `programs.py` closer to an interface layer: request handling, permissions, command calls, messages and render/redirect flow.

## Deferred deliberately

### Splitting `notas/domain/models.py`

The monolithic model file is still large, but splitting Django models is a higher-risk change than URL or view helper extraction because it can affect model discovery, migrations, admin imports and future migration diffs.

Superseded by decision 0172. PAR08 completed the dedicated split with a full
Django check, migration dry-run, boundary tests and compatibility imports.

Recommended future package shape, only when justified:

```text
notas/domain/models/
  __init__.py
  accounts.py
  foods.py
  meals.py
  dailyplans.py
  programs.py
  proposals.py
  shares.py
  comparisons.py
```
