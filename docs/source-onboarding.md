# Source Discovery and Verification

This document defines how a candidate organization or calendar becomes an approved CivicCal ingestion source.

## Organization first, feed second

An organization may be listed even when it has no machine-readable calendar. Keep its organization profile and set its verification status honestly. Do not invent feed URLs or imply that an organization participates in CivicCal.

Useful organization categories include:

- Local government, boards, commissions, and townships
- Schools, libraries, and park/recreation districts
- Churches and other faith communities
- Civic, service, veterans', fraternal, and neighborhood groups
- Clubs, youth organizations, and parent/teacher groups
- Nonprofits, charities, food pantries, and volunteer networks
- Arts, culture, history, and community-interest groups

## Discovery order

For each organization, look for event sources in this order:

1. Official iCalendar / ICS feed or calendar subscription link.
2. Official RSS or Atom event feed.
3. Documented public JSON API.
4. Official event platform with a public calendar view or export.
5. Official website event listing, only after reviewing access rules.
6. Email/mailbox ingestion is deferred from the MVP and requires a separate product decision and explicit authorization.

Prefer feeds and documented interfaces over HTML scraping. Do not bypass logins, CAPTCHAs, paywalls, or technical access controls.

## Verification checklist

Before adding a source record:

- Confirm the organization is active and the identity matches the local organization.
- Confirm the exact URL is published by the organization or otherwise authorized.
- Confirm the endpoint actually exposes event information.
- Identify timezone, recurrence behavior, cancellation behavior, and stable event IDs where possible.
- Review the site's terms and robots rules and record the review.
- Set an appropriate polling interval and honor rate limits.
- Classify access as public, registration-required, members-only, mixed, or unknown.
- Record the date and method of verification.
- Keep the source disabled until every required check is complete.

The registry validator intentionally blocks polling unless a source is approved, its terms and robots checks are recorded, and a verification timestamp and interval exist.

## Event access labels

- **Public:** anyone may attend.
- **Registration required:** public audience, but registration or tickets are needed.
- **Members only:** do not publish as a general public event; retain only if there is a justified, authorized use case and access is clearly labeled.
- **Mixed:** the organization publishes both public and restricted events; filter or label each event individually.
- **Unknown:** do not assume the event is public.

## Source health and change handling

Use ETag and Last-Modified headers where supported. Store content hashes as a fallback. Apply jitter, per-domain concurrency limits, exponential backoff, and Retry-After.

A failed fetch is not evidence that an event was cancelled. A missing event should be marked as a possible disappearance and confirmed through later successful observations or an explicit cancellation.

## Mailbox sources

Mailbox monitoring must be explicitly registered and scoped to a mailbox, folder/label, and approved sender rules. Do not monitor a personal inbox indiscriminately. Treat all messages and attachments as untrusted input. Never execute attachments or automatically reply.

## Adding a source

Add an organization to `data/sources.json` first. Then add a source record only when the exact event endpoint and review details are known. Run:

```bash
python3 scripts/validate_registry.py
```

Do not set `polling_enabled` to true until the verification checklist is complete.
