# ARCHITECTURE

This project follows a domain-first architecture.

Principles:
- Models contain business logic
- Views orchestrate, never compute
- Templates are declarative only
- Services handle permissions and rules

Aggregates (totals, allocs) are never stored.
This prevents drift and allows future rule changes.