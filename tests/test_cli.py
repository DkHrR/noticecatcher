import sys
from pathlib import Path

from cli import run_cli


def test_cli_engine_not_imported_at_top_level():
    sys.modules.pop("engine", None)
    if "cli" in sys.modules:
        del sys.modules["cli"]

    import cli  # noqa: F401

    assert "engine" not in sys.modules, "cli.py must not import engine at module top level"


def test_cli_with_stub(tmp_path, capsys):
    sample_path = Path(__file__).resolve().parent.parent / "samples" / "sample_android.txt"
    out_file = tmp_path / "test_out.ics"

    stub_fixture = [
        {
            "message_id": 7,
            "kind": "notice",
            "title": "Final Exam for CS301",
            "date_text": "28/10/2026",
            "time_text": "10:00 AM",
        },
        {
            "message_id": 23,
            "kind": "cancel",
            "title": "Guest lecture on Robotics",
            "date_text": "18/10/2026",
            "time_text": None,
        },
        {
            "message_id": 999,
            "kind": "notice",
            "title": "Non-existent message",
            "date_text": "28/10/2026",
            "time_text": None,
        },
    ]

    def stub_extract(messages):
        return stub_fixture

    result = run_cli(
        str(sample_path),
        out_file_path=str(out_file),
        extract_fn=stub_extract,
    )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "Final Exam for CS301" in content

    assert len(result["events"]) == 1
    assert len(result["cancelled"]) == 1
    assert len(result["needs_check"]) == 1

    captured = capsys.readouterr().out
    assert "Events: 1, Cancelled: 1, Needs Check: 1" in captured
    assert "Event: Final Exam for CS301 | Start: 2026-10-28 10:00:00" in captured
    assert "Cancelled: Guest lecture on Robotics" in captured
    assert "Needs Check: Non-existent message" in captured
