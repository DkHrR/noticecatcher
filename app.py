import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from flask import Flask, jsonify, make_response, render_template, request, Response

EXPIRATION_SECONDS = 15 * 60


def create_app(run_fn: Optional[Callable[[str], Any]] = None) -> Flask:
    app = Flask(__name__)
    jobs: Dict[str, Dict[str, Any]] = {}
    lock = threading.Lock()

    @app.route("/", methods=["GET"])
    def index():
        preview = os.environ.get("PREVIEW_DATA") == "1"
        return render_template("index.html", preview=preview)

    @app.route("/run-sample", methods=["POST"])
    def run_sample():
        if run_fn is None:
            return Response("not wired yet", status=501, mimetype="text/plain")

        sample_file = Path(__file__).resolve().parent / "samples" / "sample_android.txt"
        if not sample_file.exists():
            return Response("Sample chat file not found", status=404, mimetype="text/plain")

        chat_text = sample_file.read_text(encoding="utf-8")
        job_id = str(uuid.uuid4())

        with lock:
            jobs[job_id] = {
                "status": "running",
                "created_at": time.time(),
                "result": None,
                "error": None,
            }

        def worker():
            try:
                result = run_fn(chat_text)
                with lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "completed"
                        jobs[job_id]["result"] = result
            except Exception as e:
                with lock:
                    if job_id in jobs:
                        jobs[job_id]["status"] = "failed"
                        jobs[job_id]["error"] = str(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        return jsonify({"job_id": job_id})

    @app.route("/status/<job_id>", methods=["GET"])
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

    @app.route("/download/<job_id>.ics", methods=["GET"])
    def download_ics(job_id: str):
        with lock:
            job = jobs.get(job_id)
            if not job:
                return Response("Job not found", status=404, mimetype="text/plain")

            if time.time() - job["created_at"] > EXPIRATION_SECONDS:
                jobs.pop(job_id, None)
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

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=True, port=5000)
