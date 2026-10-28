# OpenAI and Stripe billing workflow

Use this reference only when the authorized source is OpenAI's billing history or
an OpenAI invoice hosted by Stripe.

## Source interpretation

- The authenticated billing history establishes the transaction inventory and
  provider-reported payment state.
- Open each unique invoice detail to capture the invoice number, billed service,
  invoice or payment date, amount, currency, and payment method identifier.
- A hosted invoice or download URL may be signed and short-lived. It is useful for
  the current extraction, but it is not a durable evidence URL.
- Download and archive the original PDF when the repository and write authority are
  available. Until then, record an evidence backlog and keep archive-link fields
  empty.
- Do not infer VAT, net amount, tax base, or Chilean DTE treatment from the absence
  of a tax line in one sample invoice. Extract those fields per document or leave
  them pending for tax review.

## My Scoope mappings currently configured

- API `Credits` and `Credits auto-reload`: `5.02 IA y procesamiento`.
- `ChatGPT Plus`: `5.03 Software y productividad`.

These mappings reflect the current financial register. If OpenAI introduces another
product label or currency, or the accounting owner changes the chart, route it for
classification instead of extending the mapping silently.

## Efficient extraction

1. Read the visible transaction history once and collect all rows in the requested
   period.
2. Visit invoice details in bounded batches and normalize them before any sheet
   write.
3. Compare the complete normalized set with the document register and payment
   register in memory.
4. Perform one grouped write for documents and payments, then one independent read
   to verify the result.

Avoid downloading each PDF serially merely to discover fields already present in
the billing history and invoice detail. PDF archiving is a separate evidence task
and may be resumed without repeating the ledger reconciliation.

## Verification checklist

- invoice identifiers are unique and any expected sequence has no unexplained gap;
- document and payment counts match the provider inventory;
- each payment references the correct document;
- month and currency totals match the provider source;
- subscription products use the software account and API usage uses the processing
  account;
- provider-paid records remain `SIN_CONCILIAR` until bank evidence is matched;
- purchase-invoice, DTE, and filing statuses remain open until the tax workflow
  supplies evidence.
