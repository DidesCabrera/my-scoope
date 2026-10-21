# MCP source map

Use live sources in this order according to the question being answered. Connector availability can vary by Codex session; never substitute guessed data for an unavailable source.

## Sentry: application behavior

Use the organization-scoped My Scoope connection to cover both the `mobile` and `python-django` projects.

Best for:

- new and regressed errors, crash frequency, affected users, stack traces, releases, and breadcrumbs;
- correlating client failures with `mobile.api.request_id`;
- confirming whether a fix stopped an error in a newer release.

Keep searches as narrow as possible by project, environment, release, route, issue, and time window. Read-only investigation is the default.

## Expo/EAS and TestFlight: tester and build context

Best for:

- EAS build/workflow status and release metadata;
- TestFlight crash reports and tester feedback exposed through the connected Expo capability;
- determining whether a tester's installed build could contain a particular change.

Do not assume a repository commit is present in TestFlight. Confirm the build/version relationship.

Before counting Expo as active coverage, compare the Expo version in `mobile/package.json` with the current prerequisite in Expo's official MCP documentation. If the project is not on the documented supported SDK, run only a read-only live capability check after authentication. Treat TestFlight/EAS coverage as unverified if that check cannot list the project's builds or feedback. Do not upgrade Expo as part of an incident review; route that as a separate release/dependency decision.

## Render: server and deployment evidence

Use Render's official Codex integration when available. Do not add a second manual MCP connection with the same provider; duplicate connections can create authentication failures and ambiguous tool selection.

Best for:

- backend logs, request correlation, service metrics, deploy history, and runtime health;
- matching a support code or Sentry `mobile.api.request_id` with a Render request identifier;
- distinguishing a client navigation problem from an API/server failure.

Render tools can include mutating operations. Use reads only unless the user explicitly authorizes a specific deploy, rollback, environment, or service change.

## Repository: implementation truth

Use source, migrations, tests, authoritative decisions, and current feature documentation to validate hypotheses. Do not infer product behavior from the Human Knowledge Center. Follow `AGENTS.md` and the smallest relevant validation tier.

## GitHub: durable coordination

Use connected GitHub history to search for duplicates and understand existing work. Issue creation, editing, assignment, labeling, commenting, and closing require explicit user authorization. An incident packet can be prepared without creating an issue.

## Minimum coverage statement

Every health review must state which of these were actually checked:

- mobile Sentry;
- backend Sentry;
- TestFlight/EAS;
- Render;
- issue history when deduplication matters.

If a source is unavailable, name it and reduce confidence only where its absence affects the conclusion.
