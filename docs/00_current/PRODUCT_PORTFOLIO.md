# Product Portfolio - My Scoope

Status: current
Last updated: 2026-07-18

## Purpose

The portfolio expresses My Scoope's current product bets as hypotheses with evidence,
next experiments, and signals to continue or reformulate. It is not a fixed feature
roadmap and does not require invented deadlines.

The machine-readable source is `docs/00_current/product_portfolio.json`. Query it with:

```bash
python manage.py project_portfolio
python manage.py project_portfolio --json
```

## Decision posture

- A bet may continue when evidence justifies more investment.
- A useful discovery may change the experiment without rewriting the objective.
- A reformulation signal is information, not automatic failure.
- Reversibility affects the size of the experiment and review needed.
- Product evidence outranks completion of a predetermined patch sequence.

## Current portfolio

| Bet | Stage | Next evidence |
| --- | --- | --- |
| Generic food coverage for Chile | Validate | Governed staging samples and real selection quality |
| AI-assisted first useful plan | Validate | Complete staging journeys and behavioral/product evidence |
| Solver V2 controlled quality | Validate | Shadow comparison over real solver-ready snapshots |
| Operational confidence | Validate | Staging contrast of Project Control signals |
| Launch readiness | Planned | Environment and operational checklist evidence |
