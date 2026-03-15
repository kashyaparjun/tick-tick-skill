"""Date/time helpers for TickTick fields.

TickTick task payloads contain ISO-like strings in fields like `dueDate`.
We normalize and interpret them in the system local timezone so that
"due today" matches what humans expect.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, tzinfo


def _normalize_iso8601(dt: str) -> str:
    s = dt.strip()
    if s.endswith("Z"):
        return s[:-1] + "+00:00"

    # Convert trailing "+HHMM" / "-HHMM" into "+HH:MM" / "-HH:MM".
    match = re.match(r"^(.*)([+-])(\d{2})(\d{2})$", s)
    if match:
        prefix, sign, hh, mm = match.groups()
        return f"{prefix}{sign}{hh}:{mm}"

    return s


def parse_ticktick_datetime(value: str | None, target_tz: tzinfo | None = None) -> datetime | None:
    if not value:
        return None

    normalized = _normalize_iso8601(value)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    if target_tz is None:
        target_tz = datetime.now().astimezone().tzinfo

    return parsed.astimezone(target_tz)


def local_date_yyyy_mm_dd(value: str | None, target_tz: tzinfo | None = None) -> str | None:
    parsed = parse_ticktick_datetime(value, target_tz=target_tz)
    if not parsed:
        return None
    return parsed.date().isoformat()
