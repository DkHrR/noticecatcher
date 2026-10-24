from datetime import date, datetime, time

from resolver import resolve


def make_msg(msg_id: int, dt: datetime, sender: str = "Aarav", text: str = "hi"):
    return {"id": msg_id, "timestamp": dt, "sender": sender, "text": text}


def test_missing_message_id():
    messages = [make_msg(1, datetime(2026, 10, 10, 10, 0))]
    notice = {"message_id": 999, "kind": "notice", "title": "Exam", "date_text": "28/10/2026"}
    res = resolve(notice, messages)
    assert res["status"] == "check"
    assert "not found" in res["reason"]


def test_dd_mm_dates():
    # Source message on Oct 10, 2026
    messages = [make_msg(1, datetime(2026, 10, 10, 10, 0))]

    for date_str in ("28/10/2026", "28/10/26", "28 Oct", "28 October 2026"):
        notice = {"message_id": 1, "kind": "notice", "title": "Exam", "date_text": date_str}
        res = resolve(notice, messages)
        assert res["status"] == "ok", f"Failed for {date_str}: {res.get('reason')}"
        assert res["date"] == date(2026, 10, 28)


def test_relative_days():
    # Source message on Wednesday Oct 14, 2026
    messages = [make_msg(1, datetime(2026, 10, 14, 8, 30))]

    # today
    res_today = resolve({"message_id": 1, "kind": "notice", "title": "T", "date_text": "today"}, messages)
    assert res_today["status"] == "ok"
    assert res_today["date"] == date(2026, 10, 14)

    # tomorrow
    res_tom = resolve({"message_id": 1, "kind": "notice", "title": "T", "date_text": "tomorrow"}, messages)
    assert res_tom["status"] == "ok"
    assert res_tom["date"] == date(2026, 10, 15)

    # day after tomorrow
    res_dat = resolve({"message_id": 1, "kind": "notice", "title": "T", "date_text": "day after tomorrow"}, messages)
    assert res_dat["status"] == "ok"
    assert res_dat["date"] == date(2026, 10, 16)


def test_weekdays():
    # Source message on Wednesday Oct 14, 2026
    messages = [make_msg(1, datetime(2026, 10, 14, 8, 30))]

    # "next Monday": first Monday strictly after Wednesday Oct 14 is Oct 19
    res_nm = resolve({"message_id": 1, "kind": "notice", "title": "W", "date_text": "next Monday"}, messages)
    assert res_nm["status"] == "ok"
    assert res_nm["date"] == date(2026, 10, 19)
    assert res_nm["date"].weekday() == 0  # Monday

    # "this Friday": next Friday on or after Wednesday Oct 14 is Oct 16
    res_tf = resolve({"message_id": 1, "kind": "notice", "title": "W", "date_text": "this Friday"}, messages)
    assert res_tf["status"] == "ok"
    assert res_tf["date"] == date(2026, 10, 16)
    assert res_tf["date"].weekday() == 4  # Friday

    # Source on Friday Oct 16: "this Friday" should be Oct 16
    msg_fri = [make_msg(2, datetime(2026, 10, 16, 8, 0))]
    res_tf_same = resolve({"message_id": 2, "kind": "notice", "title": "W", "date_text": "this Friday"}, msg_fri)
    assert res_tf_same["date"] == date(2026, 10, 16)

    # Source on Friday Oct 16: "next Friday" strictly after should be Oct 23
    res_nf_next = resolve({"message_id": 2, "kind": "notice", "title": "W", "date_text": "next Friday"}, msg_fri)
    assert res_nf_next["date"] == date(2026, 10, 23)


def test_unclear_and_invalid_dates():
    messages = [make_msg(1, datetime(2026, 10, 14, 8, 30))]

    for unclear in ("sometime next week", "sometime next month", "soon", "next month", ""):
        res = resolve({"message_id": 1, "kind": "notice", "title": "U", "date_text": unclear}, messages)
        assert res["status"] == "check", f"Expected check for '{unclear}'"

    # Invalid calendar date 31/02/2026
    res_inv = resolve({"message_id": 1, "kind": "notice", "title": "Inv", "date_text": "31/02/2026"}, messages)
    assert res_inv["status"] == "check"
    assert "Invalid calendar date" in res_inv["reason"]


def test_past_date():
    # Source message on Oct 14, 2026, but notice date is Oct 10, 2026
    messages = [make_msg(1, datetime(2026, 10, 14, 8, 30))]
    res_past = resolve({"message_id": 1, "kind": "notice", "title": "Past", "date_text": "10/10/2026"}, messages)
    assert res_past["status"] == "check"
    assert "before message date" in res_past["reason"]


def test_time_parsing_and_all_day():
    messages = [make_msg(1, datetime(2026, 10, 14, 8, 30))]

    # 10:00 AM
    r1 = resolve({"message_id": 1, "kind": "notice", "title": "T1", "date_text": "28/10/2026", "time_text": "10:00 AM"}, messages)
    assert r1["status"] == "ok"
    assert not r1["is_all_day"]
    assert r1["time"] == time(10, 0)

    # 2 pm
    r2 = resolve({"message_id": 1, "kind": "notice", "title": "T2", "date_text": "28/10/2026", "time_text": "2 pm"}, messages)
    assert r2["status"] == "ok"
    assert not r2["is_all_day"]
    assert r2["time"] == time(14, 0)

    # 14:00
    r3 = resolve({"message_id": 1, "kind": "notice", "title": "T3", "date_text": "28/10/2026", "time_text": "14:00"}, messages)
    assert r3["status"] == "ok"
    assert not r3["is_all_day"]
    assert r3["time"] == time(14, 0)

    # No time -> all-day
    r4 = resolve({"message_id": 1, "kind": "notice", "title": "T4", "date_text": "28/10/2026", "time_text": None}, messages)
    assert r4["status"] == "ok"
    assert r4["is_all_day"]
    assert r4["time"] is None


def test_cancel_notice():
    messages = [make_msg(1, datetime(2026, 10, 12, 9, 0))]
    notice = {"message_id": 1, "kind": "cancel", "title": "Robotics Lecture", "date_text": "18/10/2026", "time_text": None}
    res = resolve(notice, messages)
    assert res["status"] == "ok"
    assert res["kind"] == "cancel"
