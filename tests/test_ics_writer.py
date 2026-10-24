from datetime import date, time

from ics_writer import build_ics, escape_ics_text


def test_escape_ics_text():
    text = "Exam; Part 1, Room A\nBring: ID card\\laptop"
    escaped = escape_ics_text(text)
    assert r"\;" in escaped
    assert r"\," in escaped
    assert r"\\laptop" in escaped
    assert r"\nBring:" in escaped


def test_build_ics_format_and_crlf():
    events = [
        {
            "status": "ok",
            "kind": "notice",
            "title": "CS301 Final Exam",
            "date": date(2026, 10, 28),
            "time": time(10, 0),
            "is_all_day": False,
            "message_id": 7,
            "sender": "Prof. Sharma",
        },
        {
            "status": "ok",
            "kind": "notice",
            "title": "All Day Project Submission",
            "date": date(2026, 10, 20),
            "time": None,
            "is_all_day": True,
            "message_id": 16,
            "sender": "Prof. Sharma",
        },
        # Cancel notice should be excluded
        {
            "status": "ok",
            "kind": "cancel",
            "title": "Guest lecture",
            "date": date(2026, 10, 18),
            "time": None,
            "message_id": 23,
        },
        # Check status should be excluded
        {
            "status": "check",
            "kind": "notice",
            "title": "Unclear",
            "date": date(2026, 11, 1),
            "time": None,
            "message_id": 30,
        },
    ]

    ics = build_ics(events)

    # UTF-8 encodable
    encoded = ics.encode("utf-8")
    assert len(encoded) > 0

    # Strict CRLF line endings
    assert "\r\n" in ics
    assert ics.count("\n") == ics.count("\r\n")

    # Structure
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.endswith("END:VCALENDAR\r\n")
    assert "TZID:Asia/Kolkata" in ics

    # Should only contain 2 VEVENT blocks
    assert ics.count("BEGIN:VEVENT") == 2
    assert ics.count("END:VEVENT") == 2

    # Timed event checks
    assert "DTSTART;TZID=Asia/Kolkata:20261028T100000" in ics
    assert "DTEND;TZID=Asia/Kolkata:20261028T110000" in ics

    # All-day event checks
    assert "DTSTART;VALUE=DATE:20261020" in ics
    assert "DTEND;VALUE=DATE:20261021" in ics

    # Check stability of UIDs
    ics_second = build_ics(events)
    assert ics == ics_second
