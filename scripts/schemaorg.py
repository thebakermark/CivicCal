"""Pure projection from CivicCal normalized events to Schema.org Event.

This adapter is deliberately one-way and loss-aware: CivicCal remains the
system of record. Unsupported or ambiguous values are omitted rather than
guessed, while the original normalized record remains untouched.
"""
from __future__ import annotations

from typing import Any


SCHEMA_CONTEXT = "https://schema.org"
SCHEMA_EVENT = "https://schema.org/Event"
EVENT_STATUS = {
    "scheduled": "https://schema.org/EventScheduled",
    "cancelled": "https://schema.org/EventCancelled",
    "postponed": "https://schema.org/EventPostponed",
    "rescheduled": "https://schema.org/EventRescheduled",
}
ATTENDANCE_MODE = {
    "offline": "https://schema.org/OfflineEventAttendanceMode",
    "online": "https://schema.org/OnlineEventAttendanceMode",
    "mixed": "https://schema.org/MixedEventAttendanceMode",
}


def _nonblank(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _temporal(value: Any) -> str | None:
    """Expose valid date/date-time strings without assigning missing zones."""
    if not isinstance(value, dict):
        return None
    raw = _nonblank(value.get("value"))
    if not raw or value.get("kind") not in {"date", "date-time"}:
        return None
    return raw


def _place(value: Any) -> dict | None:
    if isinstance(value, str):
        name = _nonblank(value)
        return {"@type": "Place", "name": name} if name else None
    if not isinstance(value, dict):
        return None
    place: dict[str, Any] = {"@type": "Place"}
    name = _nonblank(value.get("name"))
    if name:
        place["name"] = name
    address = value.get("address")
    if isinstance(address, (str, dict)) and address:
        place["address"] = address
    if len(place) == 1:
        return None
    return place


def _organizer(value: Any) -> dict | None:
    if isinstance(value, str):
        name = _nonblank(value)
        return {"@type": "Organization", "name": name} if name else None
    if not isinstance(value, dict):
        return None
    organizer: dict[str, Any] = {"@type": "Organization"}
    name = _nonblank(value.get("name"))
    url = _nonblank(value.get("url"))
    if name:
        organizer["name"] = name
    if url:
        organizer["url"] = url
    return organizer if len(organizer) > 1 else None


def to_schemaorg_event(event: dict) -> dict:
    """Return a Schema.org Event projection of one normalized CivicCal event.

    No CivicCal state is mutated. Unknown values, internal IDs, source
    provenance, approval, and uncertain temporal values are not fabricated
    into Schema.org properties.
    """
    if not isinstance(event, dict):
        raise TypeError("event must be a normalized event object")

    result: dict[str, Any] = {
        "@context": SCHEMA_CONTEXT,
        "@type": "Event",
    }

    name = _nonblank(event.get("title"))
    description = _nonblank(event.get("description"))
    url = _nonblank(event.get("event_url"))
    image = _nonblank(event.get("image_url"))
    if name:
        result["name"] = name
    if description:
        result["description"] = description
    if url:
        result["url"] = url
    if image:
        result["image"] = image

    start = _temporal(event.get("start"))
    end = _temporal(event.get("end"))
    if start:
        result["startDate"] = start
    if end:
        result["endDate"] = end

    place = _place(event.get("location"))
    if place:
        result["location"] = place

    organizer = _organizer(event.get("organizer"))
    if organizer:
        result["organizer"] = organizer

    status = EVENT_STATUS.get(event.get("status"))
    if status:
        result["eventStatus"] = status

    attendance = ATTENDANCE_MODE.get(event.get("attendance_mode"))
    if attendance:
        result["eventAttendanceMode"] = attendance

    if isinstance(event.get("is_free"), bool):
        result["isAccessibleForFree"] = event["is_free"]

    categories = event.get("categories")
    if isinstance(categories, list):
        values = [item.strip() for item in categories
                  if isinstance(item, str) and item.strip()]
        if values:
            result["keywords"] = values

    audience = event.get("audience")
    if isinstance(audience, str) and audience.strip():
        result["audience"] = {"@type": "Audience", "audienceType": audience.strip()}
    elif isinstance(audience, list):
        values = [item.strip() for item in audience
                  if isinstance(item, str) and item.strip()]
        if values:
            result["audience"] = [
                {"@type": "Audience", "audienceType": item} for item in values
            ]

    registration_url = _nonblank(event.get("registration_url"))
    if registration_url:
        result["potentialAction"] = {
            "@type": "RegisterAction",
            "target": registration_url,
        }

    publisher_id = _nonblank(event.get("source_event_id"))
    if publisher_id:
        result["identifier"] = publisher_id

    return result
