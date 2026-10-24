import sys
import time
from pathlib import Path


def test_engine_not_imported_after_import_app():
    # Ensure engine is not loaded
    sys.modules.pop("engine", None)
    if "app" in sys.modules:
        del sys.modules["app"]

    import app  # noqa: F401

    assert "engine" not in sys.modules, "engine must not be imported by app.py"


def test_page_loads():
    import app

    flask_app = app.create_app()
    client = flask_app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"NoticeCatcher" in res.data
    assert b"Try the sample chat" in res.data


def test_501_when_run_fn_none():
    import app

    flask_app = app.create_app(run_fn=None)
    client = flask_app.test_client()
    res = client.post("/run-sample")
    assert res.status_code == 501
    assert res.data.decode("utf-8") == "not wired yet"


def test_job_completes_with_stub_and_status_route():
    import app

    def stub_run(text: str):
        assert len(text) > 0
        return {
            "notices": [
                {
                    "title": "CS301 Final Exam",
                    "date": "28/10/2026",
                    "time": "10:00 AM",
                    "kind": "notice",
                    "sender": "Prof. Sharma",
                }
            ],
            "needs_check": [
                {
                    "title": "Sports Day",
                    "words": "sometime next month",
                    "sender": "Rohan",
                }
            ],
            "ics": "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nSUMMARY:CS301 Final Exam\r\nEND:VCALENDAR\r\n",
        }

    flask_app = app.create_app(run_fn=stub_run)
    client = flask_app.test_client()

    res = client.post("/run-sample")
    assert res.status_code == 200
    data = res.get_json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll status
    status_data = {}
    for _ in range(30):
        s_res = client.get(f"/status/{job_id}")
        assert s_res.status_code == 200
        status_data = s_res.get_json()
        if status_data.get("status") == "completed":
            break
        time.sleep(0.05)

    assert status_data.get("status") == "completed"
    assert "result" in status_data
    notices = status_data["result"]["notices"]
    assert len(notices) == 1
    assert notices[0]["title"] == "CS301 Final Exam"


def test_ics_download_works():
    import app

    dummy_ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nSUMMARY:Assignment 2\r\nEND:VCALENDAR\r\n"

    def stub_run(text: str):
        return {"notices": [], "needs_check": [], "ics": dummy_ics}

    flask_app = app.create_app(run_fn=stub_run)
    client = flask_app.test_client()

    res = client.post("/run-sample")
    job_id = res.get_json()["job_id"]

    for _ in range(30):
        s_res = client.get(f"/status/{job_id}")
        if s_res.get_json().get("status") == "completed":
            break
        time.sleep(0.05)

    dl_res = client.get(f"/download/{job_id}.ics")
    assert dl_res.status_code == 200
    assert dl_res.headers["Content-Type"] == "text/calendar; charset=utf-8"
    assert f'filename="notices_{job_id}.ics"' in dl_res.headers["Content-Disposition"]
    assert dl_res.data.decode("utf-8") == dummy_ics


def test_preview_data_banner(monkeypatch):
    import app

    monkeypatch.setenv("PREVIEW_DATA", "1")
    flask_app = app.create_app()
    client = flask_app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"PREVIEW DATA - NOT REAL OUTPUT" in res.data


def test_results_expire():
    import app

    def stub_run(text: str):
        return {"notices": [], "needs_check": [], "ics": "CAL"}

    flask_app = app.create_app(run_fn=stub_run)
    client = flask_app.test_client()

    res = client.post("/run-sample")
    job_id = res.get_json()["job_id"]

    # Wait for completion
    for _ in range(30):
        s_res = client.get(f"/status/{job_id}")
        if s_res.get_json().get("status") == "completed":
            break
        time.sleep(0.05)

    # Fast forward time by simulating expiration on the internal job record
    # Find job dict from test app instance
    # Alternatively monkeypatch time.time
    t0 = time.time() + 16 * 60
    import unittest.mock
    with unittest.mock.patch("time.time", return_value=t0):
        s_expired = client.get(f"/status/{job_id}")
        assert s_expired.status_code == 410

        dl_expired = client.get(f"/download/{job_id}.ics")
        assert dl_expired.status_code == 410
