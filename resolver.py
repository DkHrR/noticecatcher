import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def parse_time_text(time_str: Optional[str]) -> Optional[time]:
    if not time_str or str(time_str).strip().lower() in ("none", "null", ""):
        return None

    cleaned = re.sub(r"[\s\u202f\u00a0]+", " ", str(time_str)).strip().lower()
    am_pm = None
    if "am" in cleaned:
        am_pm = "am"
        cleaned = cleaned.replace("am", "").strip()
    elif "pm" in cleaned:
        am_pm = "pm"
        cleaned = cleaned.replace("pm", "").strip()

    parts = cleaned.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0

        if am_pm == "pm" and hour != 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
            return time(hour, minute, second)
        return None
    except Exception:
        return None


def resolve_date(date_text: str, msg_date: date) -> tuple[Optional[date], Optional[str]]:
    raw = date_text.strip().rstrip(".,")
    low = raw.lower()

    if not raw:
        return None, "No date text provided"

    # Relative day words
    if low == "today":
        return msg_date, None
    if low == "tomorrow":
        return msg_date + timedelta(days=1), None
    if low in ("day after tomorrow", "the day after tomorrow"):
        return msg_date + timedelta(days=2), None

    # Weekdays: next <weekday> (first such weekday strictly after source message)
    if low.startswith("next "):
        weekday_word = low[5:].strip()
        if weekday_word in WEEKDAYS:
            target = WEEKDAYS[weekday_word]
            days_ahead = (target - msg_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return msg_date + timedelta(days=days_ahead), None

    # Weekdays: this <weekday> (next such weekday on or after source message)
    if low.startswith("this "):
        weekday_word = low[5:].strip()
        if weekday_word in WEEKDAYS:
            target = WEEKDAYS[weekday_word]
            days_ahead = (target - msg_date.weekday()) % 7
            return msg_date + timedelta(days=days_ahead), None

    # Standalone weekday (e.g. "Monday") -> next on or after, strictly after if today
    if low in WEEKDAYS:
        target = WEEKDAYS[low]
        days_ahead = (target - msg_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return msg_date + timedelta(days=days_ahead), None

    # DD/MM/YYYY or DD/MM/YY
    slash_match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", low)
    if slash_match:
        day = int(slash_match.group(1))
        month = int(slash_match.group(2))
        year = int(slash_match.group(3))
        if year < 100:
            year += 2000
        try:
            d = date(year, month, day)
            return d, None
        except ValueError:
            return None, "Invalid calendar date"

    # "28 Oct", "28 October 2026", "28 Oct 2026", "28 October"
    text_date_match = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)(?:\s+(\d{2,4}))?$", low)
    if text_date_match:
        day = int(text_date_match.group(1))
        month_str = text_date_match.group(2).lower()
        if month_str not in MONTHS:
            return None, f"Unknown month: {month_str}"
        month = MONTHS[month_str]
        year_str = text_date_match.group(3)
        year = int(year_str) if year_str else msg_date.year
        if year < 100:
            year += 2000
        try:
            d = date(year, month, day)
            return d, None
        except ValueError:
            return None, "Invalid calendar date"

    # Anything else (e.g. "sometime next week", "soon")
    return None, f"Unclear date: '{raw}'"


def resolve(notice: Dict[str, Any], messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Resolve a model-proposed notice against source chat messages using deterministic rules.
    Returns dict with status ('ok' or 'check') and a reason.
    """
    msg_id = notice.get("message_id")
    source_msg = next((m for m in messages if m.get("id") == msg_id), None)
    if not source_msg:
        return {
            "status": "check",
            "reason": f"Message ID {msg_id} not found in chat",
            "notice": notice,
        }

    msg_ts: datetime = source_msg["timestamp"]
    msg_date = msg_ts.date()

    raw_date_text = str(notice.get("date_text", "")).strip()
    resolved_d, err = resolve_date(raw_date_text, msg_date)
    if err or resolved_d is None:
        return {
            "status": "check",
            "reason": err or "Could not resolve date",
            "notice": notice,
        }

    if resolved_d < msg_date:
        return {
            "status": "check",
            "reason": f"Resolved date {resolved_d} is before message date {msg_date}",
            "notice": notice,
        }

    raw_time_text = notice.get("time_text")
    is_all_day = False
    resolved_t: Optional[time] = None

    if raw_time_text and str(raw_time_text).strip().lower() not in ("none", "null", ""):
        resolved_t = parse_time_text(str(raw_time_text))
        if resolved_t is None:
            return {
                "status": "check",
                "reason": f"Could not parse time text: '{raw_time_text}'",
                "notice": notice,
            }
    else:
        is_all_day = True

    kind = str(notice.get("kind", "notice")).lower()
    title = str(notice.get("title", "")).strip() or "Untitled Notice"

    return {
        "status": "ok",
        "reason": "",
        "kind": kind,
        "title": title,
        "date": resolved_d,
        "time": resolved_t,
        "is_all_day": is_all_day,
        "message_id": msg_id,
        "sender": source_msg.get("sender", ""),
        "source_timestamp": msg_ts,
        "notice": notice,
    }
