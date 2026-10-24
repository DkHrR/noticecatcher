import json
import time
from pathlib import Path

from engine import extract_notices
from parser import parse_chat


def main():
    sample_file = Path(__file__).resolve().parent / "samples" / "sample_android.txt"
    text = sample_file.read_text(encoding="utf-8")
    messages = parse_chat(text)

    start_time = time.time()
    try:
        notices = extract_notices(messages)
        elapsed = time.time() - start_time
        print("MODEL JSON:")
        print(json.dumps(notices, indent=2))
        print(f"Seconds taken: {elapsed:.2f}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error: {e}")
        print(f"Seconds taken: {elapsed:.2f}")


if __name__ == "__main__":
    main()
