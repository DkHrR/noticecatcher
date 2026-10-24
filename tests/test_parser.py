from datetime import datetime
from pathlib import Path

from parser import parse_chat

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_parse_android_sample():
    chat_path = SAMPLES_DIR / "sample_android.txt"
    assert chat_path.exists(), "sample_android.txt must exist"
    content = chat_path.read_text(encoding="utf-8")
    messages = parse_chat(content)

    # 42 total messages in sample - 1 system - 1 media = 40 valid messages
    assert len(messages) == 40
    for idx, msg in enumerate(messages, start=1):
        assert msg["id"] == idx
        assert isinstance(msg["timestamp"], datetime)
        assert isinstance(msg["sender"], str) and msg["sender"]
        assert isinstance(msg["text"], str)

    assert messages[0]["sender"] == "Aarav"
    assert "welcome to the Demo College" in messages[0]["text"]


def test_parse_iphone_sample():
    chat_path = SAMPLES_DIR / "sample_iphone.txt"
    assert chat_path.exists(), "sample_iphone.txt must exist"
    content = chat_path.read_text(encoding="utf-8")
    messages = parse_chat(content)

    assert len(messages) == 40
    for idx, msg in enumerate(messages, start=1):
        assert msg["id"] == idx
        assert isinstance(msg["timestamp"], datetime)
        assert isinstance(msg["sender"], str) and msg["sender"]
        assert isinstance(msg["text"], str)

    assert messages[0]["sender"] == "Aarav"
    assert "welcome to the Demo College" in messages[0]["text"]


def test_multiline_messages():
    chat_path = SAMPLES_DIR / "sample_android.txt"
    content = chat_path.read_text(encoding="utf-8")
    messages = parse_chat(content)

    exam_msg = next((m for m in messages if "Final Exam for CS301" in m["text"]), None)
    assert exam_msg is not None
    assert "\n" in exam_msg["text"]
    lines = exam_msg["text"].split("\n")
    assert len(lines) == 3
    assert lines[0] == "Urgent Notice:"
    assert "Hall A" in lines[1]
    assert "student ID cards" in lines[2]


def test_skipped_lines():
    chat_path = SAMPLES_DIR / "sample_android.txt"
    content = chat_path.read_text(encoding="utf-8")
    messages = parse_chat(content)

    for msg in messages:
        assert "<Media omitted>" not in msg["text"]
        assert "end-to-end encrypted" not in msg["text"].lower()
        assert msg["sender"] != "Messages are end-to-end encrypted"


def test_dd_mm_order():
    # Test DD/MM parsing order specifically
    android_snippet = "05/11/2026, 10:00 am - Aarav: Meeting at 10"
    parsed_android = parse_chat(android_snippet)
    assert len(parsed_android) == 1
    ts_android = parsed_android[0]["timestamp"]
    assert ts_android.day == 5
    assert ts_android.month == 11
    assert ts_android.year == 2026

    # Test iPhone DD/MM order
    iphone_snippet = "[08/12/26, 11:30:00 AM] Meera: Hello"
    parsed_iphone = parse_chat(iphone_snippet)
    assert len(parsed_iphone) == 1
    ts_iphone = parsed_iphone[0]["timestamp"]
    assert ts_iphone.day == 8
    assert ts_iphone.month == 12
    assert ts_iphone.year == 2026


def test_12h_and_24h_time():
    sample = (
        "14/10/2026, 9:41 pm - Aarav: evening 12h\n"
        "14/10/2026, 9:41 am - Aarav: morning 12h\n"
        "14/10/2026, 14:30 - Aarav: afternoon 24h\n"
        "14/10/2026, 00:15 - Aarav: midnight 24h\n"
    )
    msgs = parse_chat(sample)
    assert len(msgs) == 4
    assert msgs[0]["timestamp"].hour == 21
    assert msgs[0]["timestamp"].minute == 41

    assert msgs[1]["timestamp"].hour == 9
    assert msgs[1]["timestamp"].minute == 41

    assert msgs[2]["timestamp"].hour == 14
    assert msgs[2]["timestamp"].minute == 30

    assert msgs[3]["timestamp"].hour == 0
    assert msgs[3]["timestamp"].minute == 15
