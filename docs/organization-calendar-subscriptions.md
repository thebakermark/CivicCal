# Independent source calendar relays

## Purpose

Provide one stable iCalendar subscription URL for each registered source. Each relay is independent: it contains only events originating from that exact source. CivicCal does not need to produce a combined community calendar or organization-level aggregation.

## Source identity and isolation

An event's `source_id` identifies the source that supplied it. A source relay includes an event only when:

1. The event ID is present in the explicit publication approval manifest.
2. Its `source_id` resolves to exactly one source record in the registry.
3. The resolved source ID exactly matches the requested relay.

Do not infer source ownership from event titles, locations, descriptions, organizers, or partner relationships. An event listed by two publishers remains two source observations and may appear in each publisher's separate relay if independently approved. Cross-source duplicate detection may identify review candidates, but must not merge or delete records.

Unknown or duplicate source IDs, malformed registry entries, and events without an unambiguous source mapping fail closed. An unknown requested source returns 404. A known source with no approved events returns a valid empty calendar.

## Proposed routes

- `GET /calendars/sources/{source_id}.ics` — approved events from exactly one registered source.
- `GET /api/v1/events?source_id={source_id}` — source-filtered JSON results.

Source IDs are stable registry identifiers, not display names. Organization records remain useful for discovery and administration, but do not determine calendar relay membership.

## Publication approval

The existing explicit approval manifest remains the publication boundary. A source relay is a strict subset of approved event IDs; registering a source or capturing an event never automatically approves publication.

## Consistency and caching

- JSON and iCalendar projections must apply identical source filtering and approval rules.
- ETags must be calculated from the actual source-filtered representation.
- Last-Modified must be calculated only from approved events in that source relay.
- Keep the existing loopback-only service boundary. This design does not authorize remote hosting or deployment.
- Feed URLs are read-only subscriptions. Subscriber accounts, private feeds, and webhook delivery remain separate future capabilities.

## Tests required before implementation is complete

- A source relay includes only globally approved events from the exact requested source.
- Approved events from other sources are excluded.
- Unapproved events from the requested source are excluded.
- Unknown event source mappings are excluded rather than guessed.
- Duplicate source IDs or invalid registry structure fail closed.
- Unknown source ID returns 404; known source with no events returns a valid empty feed.
- Source-filtered JSON and ICS contain the same event IDs.
- ETag and Last-Modified are scoped to the filtered representation.
- One source's changes do not alter another source's feed validators.

## Product boundary

Each source is its own calendar relay. There is no community-wide combined calendar and no organization-wide calendar aggregation in the MVP.
