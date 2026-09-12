# Sharing operations runbook

Status: current
Date: 2026-09-11

## Runtime policy

Portable share resources expire after `SHARING_RESOURCE_TTL_DAYS` (30 by default).
The daily housekeeping job marks due resources and invitations expired, then deletes
revoked or expired resources older than `SHARING_RESOURCE_RETENTION_DAYS` only when
they have no claim. Claimed resources and their recipient-owned Inbox snapshots are
never removed by this cleanup.

Run the same command manually or from the daily scheduler:

```text
python manage.py maintain_sharing_resources --retention-days 30
```

The JSON result reports resources expired, invitations expired and unclaimed
resources deleted. Re-running the command is safe.

Preview the counts without mutating data before changing retention policy:

```text
python manage.py maintain_sharing_resources --retention-days 30 --dry-run
```

Public preview/card traffic is limited per IP; claims are limited per authenticated
user or anonymous IP; resource creation is limited per user. Production and staging
must use the shared `CACHE_URL`. Tune only through:

- `RATE_LIMIT_SHARING_PREVIEW_IP` (default `120/m`)
- `RATE_LIMIT_SHARING_CLAIM` (default `20/h`)
- `RATE_LIMIT_SHARING_CREATE_USER` (default `30/h`)

Email invitations retain their separate sender, recipient, cooldown and global
budgets. A delivery limit must never bypass the sharing-domain identity checks.

## Funnel evidence

Admin Analytics → Product Activity includes the normalized sharing cohort for the
selected period: resources, aggregate preview views, invitations, claims and saved
Inbox copies. Preview evidence is an atomic counter on the resource; it deliberately
stores no IP, user-agent or visitor identity. Use it as directional funnel evidence,
not as unique-user analytics because bots and repeated visits are included.

## Universal Links and Android App Links

The signed app declares `https://www.myscoope.com/s/*`. The server association
endpoints fail closed with HTTP 503 until real signing identity is configured:

- `MYSCOOPE_APPLE_TEAM_ID`: the 10-character Apple Developer Team ID.
- `MYSCOOPE_ANDROID_SHA256_CERT_FINGERPRINTS`: comma-separated production signing
  certificate SHA-256 fingerprints.

After Apple Developer/App Store Connect and Android production signing are ready,
configure the values on the production web service, deploy, and verify:

```text
curl -i https://www.myscoope.com/.well-known/apple-app-site-association
curl -i https://www.myscoope.com/.well-known/assetlinks.json
```

Both responses must be HTTP 200, `application/json`, contain
`com.myscoope.app`, and scope handling to `/s/*`. Then install a newly signed build
on physical devices and open a fresh `/s/<public-id>/` link from Mail and Messages.
It must open the native `/s/[id]` route and preserve that destination through login,
disclosures and onboarding. Directed `/i/*` invitations intentionally remain on the
web because their verified-email claim boundary is not represented by the public
resource route.

## Incidents and rollback

- Lower rate limits to contain abusive traffic; do not revoke unrelated resources.
- Revoke a compromised resource through its owner action/API. Preview, card and claim
  then return unavailable while existing Inbox copies remain intact.
- Disable an incorrect mobile association by removing its signing environment value;
  the endpoint returns 503 and normal HTTPS preview remains available.
- Roll back application code without reversing migrations 0058/0059. Their fields are
  additive and older code ignores them.
