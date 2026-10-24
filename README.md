# NoticeCatcher

Extracts notices, deadlines, exam dates, and cancellations from WhatsApp group chat exports into standard iCalendar (.ics) files.

## What It Does

NoticeCatcher parses exported WhatsApp group conversations (Android or iPhone format), identifies announcements with dates or deadlines, resolves dates deterministically, and writes valid `.ics` calendar events.

## How It Works

NoticeCatcher uses a hybrid architecture: **the model proposes, plain code decides**.

1. **Parser (`parser.py`)**: Reads raw text exports, handles Android (`DD/MM/YYYY, h:mm am/pm - Sender: Text`) and iPhone (`[DD/MM/YY, h:mm:ss PM] Sender: Text`) formats in 12h/24h time, preserves multi-line notices, and filters out system notifications and media lines.
2. **Model Extraction (`engine.py`)**: Sends chunked messages to an open LLM (Qwen/Qwen3-8B) with strict instructions treating chat text as untrusted data. The model proposes candidates with exact date/time words copied verbatim from the text without attempting date math.
3. **Deterministic Resolver (`resolver.py`)**: Plain Python rules validate proposed message IDs, parse DD/MM calendar dates, calculate relative offsets ("today", "tomorrow", "day after tomorrow", "next Monday", "this Friday") anchored strictly to the source message's timestamp, and separate cancellations. Any vague or unclear dates (e.g. "sometime next month") are routed to "needs your check" rather than guessed.
4. **ICS Writer (`ics_writer.py`)**: Emits RFC-compliant `.ics` files with UTF-8 encoding, CRLF (`\r\n`) line endings, proper text escaping, Asia/Kolkata timezone support, and stable UIDs. Only status "ok" notices become calendar events.

## How to Run

1. Copy `.env.example` to `.env` and configure your API key:
   ```bash
   cp .env.example .env
   ```
2. Run the CLI tool on a chat export:
   ```bash
   python cli.py samples/sample_android.txt
   ```
   By default, the calendar is saved to `out/notices.ics`.

## Tests

Run the test suite using pytest:
```bash
pytest
```

## Why Open Models

NoticeCatcher uses Qwen/Qwen3-8B served through the Tinker sampling client. The model can be swapped by updating `MODEL` in `.env`.

**Data note**: Chat text is sent to the Tinker API for inference; message text does not stay on the local device during model extraction.

## Limits

- Tested only on synthetic sample chats from "Demo College".
- Expects dates formatted in DD/MM order.
- Vague or incomplete dates are flagged as "needs your check" and not scheduled.
- The web interface (`app.py`, `templates/index.html`) is currently a UI shell with background job polling; it is not yet connected to live model runs in production.
- Measured processing speed: 68.52 s for 40 messages (including network round-trips and cold start).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
