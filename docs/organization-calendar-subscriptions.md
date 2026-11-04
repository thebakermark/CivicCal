# Organization calendar subscriptions

## Purpose

Provide one stable iCalendar subscription URL per registered organization, alongside the combined community calendar. Organization feeds are projections of the same approved event set; they are not separate ingestion pipelines.

## Ownership rule

For the first implementation, organization membership is derived from the source registry:

`source_records[].id -> source_records[].organization_id`

An identity record's `source_id` identifies its originating source. The organization feed includes an event only when:

1. Its event ID is present in the global `approved_event_ids` publication manifest.
2. Its `source_id` resolves to exactly one source record.
3. That source record has the requested `organization_id`.

This is **source ownership**, not a claim that the organization is the event host or organizer. For example, a partner event listed on the Village calendar remains attributable to the Village source in this first version. CivicCal must not infer event ownership from titles, locations, descriptions, or organizer-like text.

Unknown source IDs, duplicate source IDs, missing organization IDs, and unknown organization IDs fail closed. An event with no unambiguous source-to-organization mapping is omitted from organization feeds, but may remain in the combined community feed if it is explicitly approved there.

## Publication approval

The global publication manifest remains the single approval boundary. Organization feeds must be a strict subset of the globally approved event IDs; an organization route must never broaden publication approval or include an event simply because its source belongs to that organization.

The first implementation should derive organization membership at request time from the current source registry and identity state. This avoids duplicating event approval lists across manifests and keeps database choice independent.

## Proposed routes

- `GET /calendars/community.ics` — all globally approved events.
- `GET /calendars/organizations/{organization_id}.ics` — approved events attributed to the organization's registered sources.
- `GET /api/v1/events?organization_id={organization_id}` — organization-filtered JSON results.

Organization IDs are stable registry IDs, not display names. Unknown IDs return 404. A known organization with no approved events returns a valid empty calendar / empty result, not an error.

## Consistency and caching

- JSON and iCalendar projections must apply identical organization membership and approval rules.
- ETags must be calculated from the actual filtered representation.
- Last-Modified must be calculated only from approved records in that filtered result.
- Keep the existing loopback-only service boundary. This design does not authorize remote hosting or deployment.
- Feed URLs are read-only subscriptions. Webhook delivery, subscriber accounts, private calendars, and per-user filtering remain out of scope.

## Tests required before implementation is considered complete

- Organization feed includes only globally approved events from sources mapped to that organization.
- An approved event from another organization is excluded.
- An unapproved event from the requested organization's source is excluded.
- Unknown source mapping is excluded rather than guessed.
- Duplicate source IDs or invalid registry structure fail closed.
- Unknown organization ID returns 404; known organization with no events returns an empty valid feed.
- Organization JSON and ICS results contain the same event IDs.
- ETag and Last-Modified are scoped to the filtered representation.
- Existing community feed behavior remains unchanged.

## Deliberate limitation

Source-to-organization attribution is not the same as event organizer attribution. If a future product requirement calls for an event to appear under multiple organizations, add an explicit, reviewed event-to-organization relationship with provenance; do not infer it or silently change the meaning of source ownership.
