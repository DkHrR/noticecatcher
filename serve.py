from pathlib import Path
from typing import Any, Dict

from app import create_app


def make_app():
    import engine
    from pipeline import run_pipeline

    def run_fn(chat_text: str) -> Dict[str, Any]:
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

    return create_app(run_fn=run_fn)


if __name__ == "__main__":
    app_instance = make_app()
    app_instance.run(host="127.0.0.1", port=5000, debug=False)
