# Working dataset for catalog curation

Use a Sheet or CSV as a traceable staging surface. Keep one row per candidate record and stable column names.

## Minimum control columns

| Column | Purpose |
|---|---|
| `batch_id` | Groups one bounded curation operation. |
| `source_record_id` | Preserves the source identifier. |
| `source_name` | Identifies file, system, provider, or manual source. |
| `source_retrieved_at` | Dates the evidence snapshot. |
| `raw_name` | Preserves the original label. |
| `normalized_name` | Stores the proposed canonical label. |
| `target_record_id` | Links an authoritative record when present. |
| `action` | Add, update, merge, retain, reject, or retire. |
| `review_state` | Tracks review and publication state. |
| `quality_flags` | Lists findings without overwriting data. |
| `confidence` | Records evidence strength. |
| `decision_note` | Explains a non-obvious transformation. |
| `reviewed_by` | Identifies the responsible reviewer. |
| `reviewed_at` | Dates approval or rejection. |

## Preparation rules

- Keep raw and normalized columns separate.
- Join with identifiers rather than display names alone.
- Use controlled vocabularies and a lookup tab for repeated categories.
- Keep units in dedicated columns and flag derived values.
- Protect raw tabs when supported.
- Add summary counts by action, state, source, and quality flag.
- Export an immutable batch snapshot before an authorized import.

Before publication, reconcile row counts and identifiers, validate required fields, check duplicate keys and relationships, verify totals, inspect a representative sample, and isolate all unresolved rows.
