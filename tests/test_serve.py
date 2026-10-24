import sys
import time
from pathlib import Path


def test_serve_engine_not_imported_until_make_app():
    sys.modules.pop("engine", None)
    if "serve" in sys.modules:
        del sys.modules["serve"]

    import serve

    assert "engine" not in sys.modules, "engine must not be imported when serve is imported"

    app = serve.make_app()
    assert app is not None
    assert "engine" in sys.modules, "engine should be loaded after make_app() is called"


def test_serve_limits_and_caching():
    import serve

    def slow_stub(chat_text):
        time.sleep(0.3)
        return {
            "events": [{"title": "Cached Event", "date": "Oct 28, 2026", "time": "10:00 AM", "kind": "notice", "sender": "Prof"}],
            "cancelled": [],
            "notices": [{"title": "Cached Event", "date": "Oct 28, 2026", "time": "10:00 AM", "kind": "notice", "sender": "Prof"}],
            "needs_check": [],
            "ics": "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
        }

    app = serve.make_app(custom_run_fn=slow_stub)
    client = app.test_client()

    # 1. Start first job
    r1 = client.post("/run-sample")
    assert r1.status_code == 200
    job1_id = r1.get_json()["job_id"]

    # 2. Concurrency limit: immediate second job should return 429
    r2 = client.post("/run-sample")
    assert r2.status_code == 429
    assert "already running" in r2.data.decode("utf-8")

    # Wait for first job to complete
    for _ in range(20):
        s1 = client.get(f"/status/{job1_id}")
        if s1.get_json().get("status") == "completed":
            break
        time.sleep(0.05)

    assert s1.get_json().get("status") == "completed"

    # 3. Cache reuse: a new run within 10 minutes reuses the cached result
    r3 = client.post("/run-sample")
    assert r3.status_code == 200
    job3_id = r3.get_json()["job_id"]
    s3 = client.get(f"/status/{job3_id}")
    # Completed immediately via cache
    assert s3.get_json().get("status") == "completed"
    assert s3.get_json()["result"]["notices"][0]["title"] == "Cached Event"


def test_serve_hourly_rate_limit(monkeypatch):
    import serve

    def fast_stub(chat_text):
        return {"events": [], "cancelled": [], "notices": [], "needs_check": [], "ics": ""}

    app = serve.make_app(custom_run_fn=fast_stub)
    client = app.test_client()

    # 20 runs within an hour should succeed
    for _ in range(20):
        res = client.post("/run-sample")
        assert res.status_code == 200

    # 21st run should hit the limit (429)
    res_limit = client.post("/run-sample")
    assert res_limit.status_code == 429
    assert "Rate limit exceeded" in res_limit.data.decode("utf-8")

    # Advancing time by > 1 hour resets the limit
    future_time = time.time() + 3601
    monkeypatch.setattr(time, "time", lambda: future_time)
    res_reset = client.post("/run-sample")
    assert res_reset.status_code == 200
