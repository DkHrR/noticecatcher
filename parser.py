import re
from datetime import datetime
from typing import Any, Dict, List, Optional

ANDROID_PATTERN = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[\s\u202f\u00a0]?[aApP]\.?[mM]\.?)?)\s*-\s*(?:([^:\n]+?):\s*(.*)|(.*))$"
)
IPHONE_PATTERN = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[\s\u202f\u00a0]?[aApP]\.?[mM]\.?)?)\]\s*(?:([^:\n]+?):\s*(.*)|(.*))$"
)


def _parse_time(time_str: str) -> tuple[int, int, int]:
    cleaned = re.sub(r"[\s\u202f\u00a0]+", " ", time_str).strip()
    am_pm_match = re.search(r"([aApP])\.?([mM])\.?$", cleaned)
    is_pm = False
    is_12h = False
    if am_pm_match:
        is_12h = True
        is_pm = am_pm_match.group(1).lower() == "p"
        time_part = cleaned[: am_pm_match.start()].strip()
    else:
        time_part = cleaned

    parts = [int(p) for p in time_part.split(":")]
    hour = parts[0]
    minute = parts[1]
    second = parts[2] if len(parts) > 2 else 0

    if is_12h:
        if is_pm:
            if hour != 12:
                hour += 12
        else:
            if hour == 12:
                hour = 0
    return hour, minute, second


def _parse_date(date_str: str) -> tuple[int, int, int]:
    # WhatsApp exports with DD/MM
    parts = [int(p) for p in date_str.split("/")]
    day, month, year = parts[0], parts[1], parts[2]
    if year < 100:
        year += 2000
    return year, month, day


def _is_media(text: str) -> bool:
    cleaned = text.strip().lower()
    if cleaned == "<media omitted>" or "<media omitted>" in cleaned:
        return True
    if cleaned.startswith("<attached:") and cleaned.endswith(">"):
        return True
    return False


def _is_system(sender: Optional[str], text: str) -> bool:
    if not sender:
        return True
    cleaned_sender = sender.strip().lower()
    cleaned_text = text.strip().lower()
    if "end-to-end encrypted" in cleaned_sender or "end-to-end encrypted" in cleaned_text:
        return True
    return False


def parse_chat(text: str) -> List[Dict[str, Any]]:
    """
    Parse a WhatsApp chat export into a list of message dicts:
    [{'id': int, 'timestamp': datetime, 'sender': str, 'text': str}, ...]
    Skips system notifications and media placeholders.
    """
    lines = text.splitlines()
    messages: List[Dict[str, Any]] = []
    current_msg: Optional[Dict[str, Any]] = None
    msg_id = 1

    for raw_line in lines:
        line = raw_line.replace("\u200e", "").replace("\u200f", "").replace("\ufeff", "")
        # Try Android format
        m_android = ANDROID_PATTERN.match(line)
        m_iphone = IPHONE_PATTERN.match(line) if not m_android else None
        match = m_android or m_iphone

        if match:
            date_part = match.group(1)
            time_part = match.group(2)
            sender_part = match.group(3)
            text_part = match.group(4) if sender_part is not None else match.group(5)

            # Check if this header line is a system or media line
            if _is_system(sender_part, text_part or "") or _is_media(text_part or ""):
                current_msg = None
                continue

            year, month, day = _parse_date(date_part)
            hour, minute, second = _parse_time(time_part)
            ts = datetime(year, month, day, hour, minute, second)

            current_msg = {
                "id": msg_id,
                "timestamp": ts,
                "sender": sender_part.strip(),
                "text": (text_part or "").strip(),
            }
            messages.append(current_msg)
            msg_id += 1
        else:
            # Continuation line for multi-line message
            if current_msg is not None:
                current_msg["text"] += "\n" + line.rstrip("\r\n")

    return messages
