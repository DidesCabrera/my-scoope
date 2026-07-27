# Email Delivery Abuse Protection Cycle

Status: completed in repository — external provider configuration and staging smoke remain
Date: 2026-07-27
Cycle code: EAP

## Objective

Protect Resend consumption without making email verification the only anti-abuse
control and without allowing non-critical share invitations to exhaust the capacity
needed by account recovery and verification.

## Implemented slices

- EAP00: audit existing signup, allauth, SMTP and share call sites.
- EAP01: add server-validated Turnstile to traditional signup.
- EAP02: add burst, daily-IP and daily-email signup limits.
- EAP03: configure a shared Redis cache path for production.
- EAP04: add persistent `EmailDeliveryAttempt` audit records.
- EAP05: centralize all five share invitation paths.
- EAP06: suppress email for existing Inbox recipients and duplicate shares.
- EAP07: add share budgets, verified-sender policy, cooldown and kill switch.
- EAP08: add deploy checks, environment contract, migrations and regressions.

## External gates

- export and classify recent Resend traffic;
- create Cloudflare Turnstile keys;
- provision Render Key Value;
- configure production environment variables;
- run staging smoke with real Resend and Cloudflare;
- decide whether Resend signed webhooks and automatic bounce suppression are needed
  after observing real volume.
