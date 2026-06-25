# API Adapter MVP

## Purpose

The API Adapter MVP is the first API-first external boundary for AI-assisted workflows in My Scoope.

Its purpose is to expose a small and safe set of AI-oriented capabilities through Django endpoints while preserving the internal architecture:

```text
HTTP request
  → API Adapter
  → Internal AI Tools Layer
  → Read / Validation / Proposal layers
  → Domain