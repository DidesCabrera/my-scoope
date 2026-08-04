# 0172 · Complete the notas model-module split

Status: accepted
Date: 2026-08-03

## Decision

`notas/domain/models.py` remains the stable public import façade but contains no
concrete Django model definitions. Operational foods, meals, daily plans and
programs move to their declared responsibility modules, completing the earlier
identity, auth, sharing, proposal, comparison, calendar and notification splits.

This is a Python-location refactor only. Model names, app labels, database table
names, relations and public compatibility imports remain unchanged. A migration
dry-run must remain empty; any future model boundary must be registered in
`DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG` and importable through the façade.
