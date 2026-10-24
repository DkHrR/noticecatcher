from typing import Any, Callable, Dict, List

from ics_writer import build_ics
from parser import parse_chat
from resolver import resolve


def run_pipeline(
    text: str,
    extract_fn: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Run the end-to-end extraction and resolution pipeline on chat export text.
    Returns: {events, cancelled, needs_check, ics}
    """
    messages = parse_chat(text)
    raw_notices = extract_fn(messages)

    events: List[Dict[str, Any]] = []
    cancelled: List[Dict[str, Any]] = []
    needs_check: List[Dict[str, Any]] = []

    for notice in raw_notices:
        resolved = resolve(notice, messages)
        if resolved.get("status") == "ok":
            if resolved.get("kind") == "cancel":
                cancelled.append(resolved)
            else:
                events.append(resolved)
        else:
            needs_check.append(resolved)

    ics_content = build_ics(events)

    return {
        "events": events,
        "cancelled": cancelled,
        "needs_check": needs_check,
        "ics": ics_content,
    }
