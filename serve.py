import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from flask import jsonify, make_response, Response
from app import create_app

EXPIRATION_SECONDS = 15 * 60
CACHE_DURATION_SECONDS = 10 * 60
MAX_HOURLY_RUNS = 20


def make_app(custom_run_fn: Optional[Callable[[str], Any]] = None):
    if custom_run_fn is not None:
        run_fn = custom_run_fn
    else:
        import engine
        from pipeline import run_pipeline

        def default_run_fn(chat_text: str) -> Dict[str, Any]:
            if not chat_text:
                sample_file = Path(__file__).resolve().parent / "samples" / "sample_android.txt"
                chat_text = sample_file.read_text(encoding="utf-8")

            result = run_pipeline(chat_text, extract_fn=engine.extract_notices)
            events = result["events"]
            cancelled = result["cancelled"]
            needs_check = result["needs_check"]
            ics_text = result["ics"]

            notices_list = []
            events_list = []
            for e in events:
                d_str = e["date"].strftime("%b %d, %Y") if hasattr(e.get("date"), "strftime") else str(e.get("date", ""))
                t_str = e["time"].strftime("%I:%M %p").lstrip("0") if hasattr(e.get("time"), "strftime") else str(e.get("time") or "")
                item = {
                    "title": e.get("title", "Notice"),
                    "date": d_str,
                    "time": t_str,
                    "kind": "notice",
                    "sender": e.get("sender", ""),
                }
                notices_list.append(item)
                events_list.append(item)

            cancelled_list = []
            for c in cancelled:
                d_str = c["date"].strftime("%b %d, %Y") if hasattr(c.get("date"), "strftime") else str(c.get("date", ""))
                t_str = c["time"].strftime("%I:%M %p").lstrip("0") if hasattr(c.get("time"), "strftime") else str(c.get("time") or "")
                item = {
                    "title": c.get("title", "Cancelled Notice"),
                    "date": d_str,
                    "time": t_str,
                    "kind": "cancel",
                    "sender": c.get("sender", ""),
                }
                notices_list.append(item)
                cancelled_list.append(item)

            needs_check_list = []
            for nc in needs_check:
                title = nc.get("title") or nc.get("notice", {}).get("title", "Unclear notice")
                words = nc.get("words") or nc.get("notice", {}).get("date_text", "")
                sender = nc.get("sender") or nc.get("notice", {}).get("sender", "")
                needs_check_list.append({
                    "title": title,
                    "words": words,
                    "sender": sender,
                    "reason": nc.get("reason", "Needs check"),
                })

            return {
                "events": events_list,
                "cancelled": cancelled_list,
                "notices": notices_list,
                "needs_check": needs_check_list,
                "ics": ics_text,
            }

        run_fn = default_run_fn

    # Initialize underlying Flask app
    app = create_app(run_fn=run_fn)

    # In-memory rate limiting and caching state
    jobs: Dict[str, Dict[str, Any]] = {}
    lock = threading.Lock()
    run_history: List[float] = []
    last_finished: Dict[str, Any] = {"result": None, "time": 0.0}

    def rate_limited_run_sample():
        nonlocal last_finished
        now = time.time()

        with lock:
            # 1. At most 1 job running at a time
            if any(j.get("status") == "running" for j in jobs.values()):
                return Response(
                    "A job is already running. Please try again shortly.",
                    status=429,
                    mimetype="text/plain",
                )

            # 2. At most 20 runs per hour in total
            active_history = [t for t in run_history if 0 <= now - t < 3600]
            run_history.clear()
            run_history.extend(active_history)

            if len(run_history) >= MAX_HOURLY_RUNS:
                return Response(
                    "Rate limit exceeded (maximum 20 runs per hour). Please try again later.",
                    status=429,
                    mimetype="text/plain",
                )

            # 3. Reuse last finished result if under 10 minutes old
            if last_finished["result"] is not None and (0 <= now - last_finished["time"] < CACHE_DURATION_SECONDS):
                cached_id = str(uuid.uuid4())
                jobs[cached_id] = {
                    "status": "completed",
                    "created_at": now,
                    "result": last_finished["result"],
                    "error": None,
                }
                run_history.append(now)
                return jsonify({"job_id": cached_id})

            # Accept run and launch background thread
            sample_file = Path(__file__).resolve().parent / "samples" / "sample_android.txt"
            chat_text = sample_file.read_text(encoding="utf-8") if sample_file.exists() else ""

            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                "status": "running",
                "created_at": now,
                "result": None,
                "error": None,
            }
            run_history.append(now)

        def worker():
            nonlocal last_finished
            try:
                res = run_fn(chat_text)
                with lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "completed"
                        jobs[job_id]["result"] = res
                        last_finished["result"] = res
                        last_finished["time"] = time.time()
            except Exception as e:
                with lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "failed"
                        jobs[job_id]["error"] = str(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        return jsonify({"job_id": job_id})

    def get_status(job_id: str):
        with lock:
            job = jobs.get(job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if time.time() - job["created_at"] > EXPIRATION_SECONDS:
                return jsonify({"error": "Results expired"}), 410

            return jsonify({
                "status": job["status"],
                "result": job["result"],
                "error": job["error"],
            })

    def download_ics(job_id: str):
        with lock:
            job = jobs.get(job_id)
            if not job:
                return Response("Job not found", status=404, mimetype="text/plain")

            if time.time() - job["created_at"] > EXPIRATION_SECONDS:
                return Response("Results expired", status=410, mimetype="text/plain")

            if job["status"] != "completed":
                return Response("Job not completed", status=400, mimetype="text/plain")

            result = job["result"]
            ics_content = ""
            if isinstance(result, dict):
                ics_content = result.get("ics", "")
            elif isinstance(result, str):
                ics_content = result

        resp = make_response(ics_content.encode("utf-8"))
        resp.headers["Content-Type"] = "text/calendar; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="notices_{job_id}.ics"'
        return resp

    # Override views on the app instance
    app.view_functions["run_sample"] = rate_limited_run_sample
    app.view_functions["get_status"] = get_status
    app.view_functions["download_ics"] = download_ics

    return app


if __name__ == "__main__":
    app_instance = make_app()
    app_instance.run(host="127.0.0.1", port=5000, debug=False)
