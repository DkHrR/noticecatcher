import hashlib
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List


def escape_ics_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def build_ics(events: List[Dict[str, Any]]) -> str:
    """
    Build a valid iCalendar (.ics) string for status 'ok' notice events.
    Uses UTF-8, CRLF line endings, Asia/Kolkata timezone, and stable UIDs.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NoticeCatcher//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Kolkata",
        "X-LIC-LOCATION:Asia/Kolkata",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0530",
        "TZOFFSETTO:+0530",
        "TZNAME:IST",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    now_utc_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for evt in events:
        # Only status 'ok' notices become events, not cancels
        if evt.get("status") != "ok" or evt.get("kind") == "cancel":
            continue

        evt_date: date = evt["date"]
        evt_time: time = evt.get("time")
        is_all_day: bool = evt.get("is_all_day", False) or evt_time is None

        # Stable UID
        uid_seed = f"{evt.get('message_id', 0)}-{evt.get('title', '')}-{evt_date.isoformat()}"
        uid_hash = hashlib.sha256(uid_seed.encode("utf-8")).hexdigest()[:16]
        uid = f"notice-{evt.get('message_id', 0)}-{uid_hash}@noticecatcher"

        summary = escape_ics_text(evt.get("title", "Notice"))
        sender = evt.get("sender", "")
        desc = escape_ics_text(f"Extracted notice from chat (Sender: {sender})")

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now_utc_stamp}")

        if is_all_day:
            start_str = evt_date.strftime("%Y%m%d")
            end_date = evt_date + timedelta(days=1)
            end_str = end_date.strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{start_str}")
            lines.append(f"DTEND;VALUE=DATE:{end_str}")
        else:
            start_dt = datetime.combine(evt_date, evt_time)
            end_dt = start_dt + timedelta(hours=1)
            start_str = start_dt.strftime("%Y%m%dT%H%M%S")
            end_str = end_dt.strftime("%Y%m%dT%H%M%S")
            lines.append(f"DTSTART;TZID=Asia/Kolkata:{start_str}")
            lines.append(f"DTEND;TZID=Asia/Kolkata:{end_str}")

        lines.append(f"SUMMARY:{summary}")
        lines.append(f"DESCRIPTION:{desc}")
        lines.append("STATUS:CONFIRMED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
