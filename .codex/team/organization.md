# AI Team Organization

Status: active
Last reviewed: 2026-11-19

```mermaid
flowchart TD
    F[Felipe Dides\nFinal authority]
    C[AI Team Capability Steward\nCapability evidence and skill lifecycle]

    F --> PM[Gestión de Proyectos]
    PM --> C
    PM --> SPA[Strategic Product Advisor]
    PM --> PWC[Parallel Work Coordinator]
    PM --> BCS[Encargado de ramas y checkouts]

    F --> PT[Producto]
    PT --> NSS[Nutrition Solver Steward]
    PT --> ACS[AI Architecture and Context Steward]
    PT --> MSRS[Mobile Store Release Steward]

    F --> AI["Asistente AI & MCP"]
    AI --> AAPS["Encargado de Asistente AI & MCP"]

    F --> SUP[Soporte]
    SUP --> OL[Líder de observabilidad]
    OL --> MIS[Especialista en incidentes móviles]
    OL --> BIS[Especialista en incidentes backend]
    OL --> RIS[Especialista en incidentes de publicación]
    OL --> IV[Verificador de incidentes]

    F --> CO[Catalog operations]
    CO --> CCS[Catalog Curation Steward]
    CO --> CIC[Creador de imágenes del catálogo]
    CO --> NDR[Investigador de datos nutricionales]
    CO --> CCP[Publicador del catálogo curado]
    CCS -. coordinates review handoffs .-> CIC
    CCS -. coordinates review handoffs .-> NDR
    CCS -. coordinates approved batches .-> CCP
    SPA -. defines product priorities .-> CCS
    ACS -. protects data boundaries .-> CCS
    SPA -. defines solver outcomes .-> NSS
    NSS -. specifies consumption contracts .-> CCS
    CCS -. supplies eligible curated data .-> NSS
    ACS -. protects solver boundaries .-> NSS
    ACS -. reviews context and boundaries .-> AAPS
    NSS -. supplies solver quality contracts .-> AAPS
    AAPS -. supplies AI diagnostics .-> OL
    PWC -. audit evidence .-> BCS
    SPA -. defines release scope .-> MSRS
    OL -. supplies health evidence .-> MSRS
    MSRS -. routes release incidents .-> RIS
    MSRS -. requests independent evidence .-> IV

    F --> FIN[Finance]
    FIN --> AIR[Accounting Intake and Recordkeeping Agent]
    FIN --> CTA[Chile Tax and SII Compliance Advisor]
    FIN --> FPA[Financial Planning Advisor]
    FIN --> FA[Funding Advisor]

    F --> CM[Commercial and marketing]
    CM --> CSA[Commercial Strategy Advisor]
    CM --> BR[Brand Identity Steward]
    CM --> CMR[Customer and Market Researcher]
    CM --> GMO[Growth and Marketing Operator]
    CM --> ROA[Revenue Operations Agent]
    CSA -. positioning .-> BR
    BR -. visual guidance .-> SPA
    BR -. store assets .-> MSRS
    BR -. catalog image style .-> CCS
    BR -. visual guidance .-> CIC

    C -. audits and recommends .-> PM
    C -. audits and recommends .-> PT
    C -. audits and recommends .-> AI
    C -. audits and recommends .-> SUP
    C -. audits and recommends .-> FIN
    C -. audits and recommends .-> CM
```

## Relationship semantics

- Solid lines group an operational responsibility or a delegation path.
- Dotted lines show capability governance. The Capability Steward does not manage
  the daily output of every role.
- Felipe can converse directly with every role and remains the final authority.
- Felipe defines the team's composition and mandates. The Capability Steward
  documents evidence and recommends changes only when Felipe requests advice.
- Gestión de Proyectos contains capability stewardship, strategic product advice,
  parallel-work coordination, and branch/checkout stewardship. The Strategic
  Product Advisor still evaluates product bets and user outcomes across projects;
  organizational placement does not transfer product implementation authority.
- Producto contains the Nutrition Solver Steward, AI Architecture and Context
  Steward, and Mobile Store Release Steward. Architecture and Context helps an AI
  understand the codebase and its current boundaries before changing it.
- Asistente AI & MCP contains the role visibly named Encargado de Asistente AI &
  MCP. Soporte contains Observability Lead and its mobile, backend, release, and
  independent verification specialists.
- The Branch and Checkout Steward owns requested Git branch, PR, and worktree
  lifecycle actions. Parallel Work Coordinator owns the read-only simultaneous
  work audit and Metro coordination. They share evidence but do not duplicate
  ownership of mutations.
- Coordinators delegate only when specialization or independent evidence adds
  value. Simple work stays with one role.
- Specialists may collaborate temporarily across boundaries, then return a compact
  evidence packet to the coordinator or Felipe.
- Catalog Operations is a permanent operating area. Its steward maintains catalog
  data quality and preparation; Product determines which coverage creates value,
  and Architecture protects authoritative data boundaries.
- Felipe defined three catalog specialists: the image creator prepares approved
  visual assets, the nutrition researcher provides source-linked dossiers, and
  the publisher executes approved data and image batches in staging and
  production. They are peers in Catalog Operations; the Catalog Curation Steward
  coordinates review handoffs and maintains the area's quality and review queue.
- The Nutrition Solver Steward owns solver quality criteria, consumption
  contracts, evaluation evidence, and the improvement backlog. Catalog Operations
  owns the source data and publication process; neither role silently changes the
  other's authority.
- The Encargado de Asistente AI & MCP owns implementation and evaluation of the
  assistant, governed action mechanisms, model integration, MCP projection, and
  AI release evidence. Architecture protects the wider system boundaries, while
  domain roles retain their calculation, data, and product authorities.
- The Mobile Store Release Steward owns release identity, reusable readiness
  evidence, submission coordination, App Store Connect operating state, and the
  recommendation to submit or hold. Product owns release scope, technical roles
  own implementation, Observability supplies health evidence, Release Incident
  Specialist investigates delivery failures, and Incident Verifier supplies
  independent final evidence when required.

## Role classes

- **Advisor:** analyzes evidence and recommends a decision.
- **Coordinator:** triages work and routes bounded investigations.
- **Operator:** executes a defined process within explicit authority.
- **Specialist:** investigates or solves a specific domain boundary.
- **Verifier:** independently checks evidence and closure conditions.
- **Steward:** maintains the quality and coherence of a durable system.

The class describes the role's primary posture, not permission to write or act in
external systems.

## Shared workflow skills

Shared workflow skills provide repeatable procedures to several roles without
creating another reporting relationship. They remain outside the organigram and
do not transfer ownership or authority. Current pilots are:

- `fresh-task-checkout`, which establishes a freshly fetched remote base and an
  isolated checkout before technical work begins;
- `mobile-simulator-review`, which establishes source, Metro, native-build, and API
  identity before presenting a mobile change for visual review.
- `publish-to-staging`, which validates and publishes the exact completed task to
  the current staging integration boundary and verifies remote CI. Checkout and
  branch housekeeping remain a separate requested outcome.
