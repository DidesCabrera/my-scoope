---
name: supplier-billing-reconciliation
description: Reconcile recurring foreign-supplier billing histories, invoices, and payment evidence with My Scoope's financial register. Use for OpenAI, Stripe-hosted invoices, cloud vendors, subscription backfills, duplicate or gap checks, payment registration, and evidence or tax handoffs. Do not use to submit DTE or tax filings, initiate payments, or claim bank reconciliation without bank evidence.
---

# Supplier Billing Reconciliation

Create a complete, traceable supplier ledger while keeping document, payment,
bank-reconciliation, evidence, and tax states independent. Communicate in Spanish
unless the user requests another language.

Read `AGENTS.md`, `.codex/team/memory/areas/finance.md`, and the target register
before changing external data. Use this as a shared workflow: the role performing
the work retains its own authority and limits. Apply the
`accounting-intake-recordkeeping-agent` boundary for recordkeeping and route tax
decisions to `chile-tax-sii-compliance-advisor`.

## Required outcome

- Every in-scope supplier invoice appears once in the document register.
- Every evidenced payment appears once and links to its document.
- Monthly counts and totals reconcile to the authorized billing source, per currency.
- Missing archives, unknown classifications, bank matches, and tax work remain
  explicit open items rather than implied completions.

## Workflow

1. Define the supplier, period, authorized billing source, durable document
   repository, target register, and approved account mapping. Read the live register
   immediately before writing.
2. Inventory the authoritative billing history in bounded batches. Capture invoice
   identifier, issue or payment date, service, currency, total, payment state, and
   payment method with only the minimum safe identifier such as brand and last four
   digits. Never retain a full card or credential.
3. Normalize records and compare them with the ledger using supplier plus invoice
   identifier as the primary duplicate key. Use date, amount, currency, and source
   identity as supporting checks. Test meaningful supplier sequences for gaps.
4. Resolve conflicts from the original invoice or provider detail. If a transaction
   list date differs because of timezone or settlement display, use the date shown
   on the invoice or payment detail and record the discrepancy when material.
5. Preserve evidence. Treat signed or session-bound hosted invoice links as
   temporary. Archive the original document in the approved repository before
   writing a durable URL. If archiving is incomplete, leave the URL empty and mark
   the evidence backlog explicitly.
6. With current authorization, add or correct document and payment records while
   preserving sheet formulas, validation, formatting, and unrelated rows. Apply only
   approved supplier-to-account mappings. Send unknown services or conflicting tax
   fields to review without guessing.
7. Keep these states separate:
   - source document found and validated;
   - payment evidenced by the provider;
   - payment matched to a bank movement;
   - document archived durably;
   - Chilean tax treatment reviewed;
   - DTE or filing prepared, submitted, and accepted.
8. Verify the result by checking unique invoice and payment identifiers, missing
   sequence members, document-to-payment links, monthly counts and totals, formulas,
   validation rules, first and last records, exceptions, and the visible sheet.
9. Report what is complete and list the remaining archive, bank, classification,
   and tax queues. A paid provider record does not prove bank reconciliation or tax
   compliance.

## Provider guidance

For OpenAI billing backed by Stripe, read
[references/openai-stripe.md](references/openai-stripe.md). Do not load that
reference for unrelated suppliers.

## Stopping conditions

Stop before writing when the target register is ambiguous, the live source and
ledger materially conflict, or no approved mapping exists. Complete the comparison
and prepare a reviewable exception list instead. Never submit a DTE, F29, amended
return, payment, or other consequential external action unless the current user
request explicitly authorizes that exact action.
