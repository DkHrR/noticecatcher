import sys
from pathlib import Path

REAL_MODEL_FIXTURE = [
    {
        "message_id": 7,
        "kind": "notice",
        "title": "Final Exam for CS301",
        "date_text": "28/10/2026",
        "time_text": "10:00 AM",
    },
    {
        "message_id": 16,
        "kind": "notice",
        "title": "Submit Assignment 2",
        "date_text": "20/10/2026",
        "time_text": "11:59 PM",
    },
    {
        "message_id": 23,
        "kind": "cancel",
        "title": "Guest lecture on Robotics",
        "date_text": "18/10/2026",
        "time_text": None,
    },
    {
        "message_id": 30,
        "kind": "notice",
        "title": "Project demo",
        "date_text": "tomorrow",
        "time_text": "2:00 PM",
    },
    {
        "message_id": 34,
        "kind": "notice",
        "title": "Workshop on Cloud Computing",
        "date_text": "next Monday",
        "time_text": "10:00 AM",
    },
]


def test_engine_not_imported_with_pipeline():
    sys.modules.pop("engine", None)
    if "pipeline" in sys.modules:
        del sys.modules["pipeline"]

    import pipeline  # noqa: F401

    assert "engine" not in sys.modules, "pipeline must not import engine at module top level"


def test_run_pipeline_with_real_model_fixture():
    from pipeline import run_pipeline

    sample_path = Path(__file__).resolve().parent.parent / "samples" / "sample_android.txt"
    sample_text = sample_path.read_text(encoding="utf-8")

    def stub_extract(messages):
        return REAL_MODEL_FIXTURE

    result = run_pipeline(sample_text, stub_extract)

    assert "events" in result
    assert "cancelled" in result
    assert "needs_check" in result
    assert "ics" in result

    # 4 notices become events (exam, assignment, demo, workshop)
    assert len(result["events"]) == 4
    # 1 cancel notice
    assert len(result["cancelled"]) == 1
    assert result["cancelled"][0]["title"] == "Guest lecture on Robotics"
    # 0 needs_check
    assert len(result["needs_check"]) == 0

    # ICS content check
    ics = result["ics"]
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert ics.count("BEGIN:VEVENT") == 4
    assert "Final Exam for CS301" in ics
    assert "Submit Assignment 2" in ics
    assert "Project demo" in ics
    assert "Workshop on Cloud Computing" in ics
    # Cancelled event must NOT be in ICS
    assert "Robotics" not in ics


def test_run_pipeline_with_unclear_notice():
    from pipeline import run_pipeline

    sample_path = Path(__file__).resolve().parent.parent / "samples" / "sample_android.txt"
    sample_text = sample_path.read_text(encoding="utf-8")

    def stub_extract(messages):
        return [
            {
                "message_id": 28,
                "kind": "notice",
                "title": "Sports Day",
                "date_text": "sometime next month",
                "time_text": None,
            }
        ]

    result = run_pipeline(sample_text, stub_extract)
    assert len(result["events"]) == 0
    assert len(result["cancelled"]) == 0
    assert len(result["needs_check"]) == 1
    assert result["needs_check"][0]["status"] == "check"
    assert "sometime next month" in result["needs_check"][0]["reason"]
