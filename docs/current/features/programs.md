# Programs

## Estado

Feature vigente y compleja.

## Conceptos principales

- Programa semanal sin fechas.
- Semanas dinámicas.
- Días de programa basados en copias/snapshots de DailyPlans.
- KPIs semanales y de programa.
- Gráficos por día/semana.
- Detail semanal dedicado.

## Ubicación de lógica

```text
notas/interface/views/programs.py
notas/presentation/viewmodels/programs.py
notas/presentation/viewmodels/program_actions.py
notas/application/services/cache/program_summary.py
```

## Reglas

- No volver a crecer `programs.py` con builders visuales extensos.
- Si se agrega lógica de gráficos, mover a presentation/viewmodels o services adecuados.
- Si se agregan writes, usar commands.
- Si en el futuro se agrega comparador de Programs, diseñarlo como feature separada, no dentro de `programs.py`.
