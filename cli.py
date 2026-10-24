import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from pipeline import run_pipeline


def run_cli(
    chat_file_path: str,
    out_file_path: str = "out/notices.ics",
    extract_fn: Optional[Callable[[list], list]] = None,
) -> dict:
    chat_path = Path(chat_file_path)
    if not chat_path.exists():
        raise FileNotFoundError(f"Chat file not found: {chat_file_path}")

    text = chat_path.read_text(encoding="utf-8")

    if extract_fn is None:
        import engine

        extract_fn = engine.extract_notices

    result = run_pipeline(text, extract_fn=extract_fn)

    events = result["events"]
    cancelled = result["cancelled"]
    needs_check = result["needs_check"]
    ics_text = result["ics"]

    # Write output .ics file
    out_path = Path(out_file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(ics_text.encode("utf-8"))

    # Print summary counts
    print(f"Events: {len(events)}, Cancelled: {len(cancelled)}, Needs Check: {len(needs_check)}")

    # Print each event
    for evt in events:
        start_str = str(evt.get("date", ""))
        if evt.get("time"):
            start_str += f" {evt['time'].strftime('%H:%M:%S')}"
        print(f"Event: {evt.get('title', 'Notice')} | Start: {start_str}")

    # Print each cancelled title
    for c in cancelled:
        print(f"Cancelled: {c.get('title', 'Cancelled Notice')}")

    # Print each needs_check item with reason
    for nc in needs_check:
        title = nc.get("title") or nc.get("notice", {}).get("title", "Unknown")
        reason = nc.get("reason", "Needs manual verification")
        print(f"Needs Check: {title} | Reason: {reason}")

    return result


def main():
    parser = argparse.ArgumentParser(description="NoticeCatcher CLI")
    parser.add_argument("chat_file", help="Path to WhatsApp chat export .txt file")
    parser.add_argument(
        "--out",
        default="out/notices.ics",
        help="Output path for generated .ics file (default: out/notices.ics)",
    )

    args = parser.parse_args()
    run_cli(args.chat_file, args.out)


if __name__ == "__main__":
    main()
