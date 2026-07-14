# Read Layer: DTOs, Queries and Permission Boundaries

## Purpose

The read layer provides structured, serializable and permission-aware access to the nutritional core of My Scoope.

Its main goal is to expose stable read contracts that can be reused by:

- Django web views.
- Future internal APIs.
- Future mobile clients.
- Future AI/MCP integrations.
- Validation and proposal workflows.

This layer does not modify data. It only reads, structures and summarizes existing domain information.

---

## Strategic Context

My Scoope is being prepared for future AI-assisted workflows.

The long-term goal is that an external or internal AI agent can help users and nutritionists by reading nutritional data, comparing plans against targets and generating proposal drafts.

However, AI should never directly modify final user plans.

The intended future workflow is:

```text
AI agent → read/query tools → create proposal → human review → approve/reject