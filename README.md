# Global Music Usage Finder

A local-first Python CLI app that looks up an **artist name** and/or **song title** and scans multiple web surfaces (including foreign markets such as Douyin) for likely usage mentions.

> ⚠️ Important: This project is designed for lawful research. Always respect each site's Terms of Service, robots rules, and local laws.

## Absolute easiest: run as an app (Windows)

1. Double-click `start_app.bat`.
2. Your browser opens automatically to `http://127.0.0.1:8000`.
3. Search artist/song in the form.

If Windows asks which app to use for `.bat`, run from Command Prompt:

```bat
cd C:\NewRaLW
start_app.bat
```

## Easiest way: use it in your browser (no coding)

If you want an app-like experience, do this in **Windows Command Prompt**:

```bat
cd C:\NewRaLW
run_web_app.bat
```

Then open this in your browser:

```text
http://127.0.0.1:8000
```

Type artist/song, click **Search**, and results show in a table.

## Tracker vs Web App (important)

- `tracker.py` = command-line tool (prints JSON in terminal, optional CSV/JSON file output).
- `web_app.py` = local website UI (form + results table in browser).
- `run_tracker.bat` runs `tracker.py`, but it needs arguments like `--artist` and/or `--song`.
- `run_web_app.bat` starts the browser UI server at `http://127.0.0.1:8000`.

If `run_tracker.bat` looked like it did nothing, it was probably started without arguments. It now prints usage/help and an example command.

## First question: do you need to download files first?

Yes — you need the project folder on your PC first.

### Option A (easiest): Download ZIP from GitHub
1. Open the repo page in your browser.
2. Click **Code** > **Download ZIP**.
3. Extract ZIP to something like `C:\NewRaLW`.
4. Open **Command Prompt** and run:

```bat
cd C:\NewRaLW
run_tracker.bat --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

### Option B: Use git clone
```bat
git clone <YOUR_REPO_URL>
cd NewRaLW
run_tracker.bat --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

## Super simple copy/paste (Windows CMD)

Copy/paste these one by one in **Command Prompt**:

```bat
cd C:\path\to\NewRaLW
```

```bat
run_tracker.bat --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

```bat
type results.json
```

If `run_tracker.bat` does not work, use:

```bat
py tracker.py --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

## Quick start (Windows Command Prompt)

1) Open **Command Prompt** and go to the project folder:

```bat
cd C:\path\to\NewRaLW
```

2) Run with Python launcher (`py`) from CMD:

```bat
py tracker.py --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

3) Or use the included batch wrapper (same result):

```bat
run_tracker.bat --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

4) CSV output example:

```bat
py tracker.py --artist "Adele" --song "Hello" --csv results.csv
```

## Quick start (macOS/Linux)

```bash
python3 tracker.py --artist "Adele" --song "Hello" --max-results 20 --out results.json
```

## Example: target Douyin heavily

```bat
py tracker.py --artist "Jay Chou" --song "青花瓷" --markets global douyin --max-results 40 --out jay_douyin.json
```

## Flags

- `--artist`: Artist name.
- `--song`: Song title.
- `--markets`: One or more of `global`, `douyin`, `tiktok`, `youtube`.
- `--max-results`: Max rows returned.
- `--out`: JSON output path.
- `--csv`: CSV output path.
- `--timeout`: HTTP timeout in seconds.

## Troubleshooting (Windows CMD)

- If `py` is not recognized, install Python from python.org and check **“Add Python to PATH”**.
- If `python` works but `py` does not, replace `py` with `python` in all commands.
- If you get zero results, retry with fewer markets and a larger timeout:

```bat
py tracker.py --artist "Adele" --song "Hello" --markets douyin --timeout 20
```

- If your network blocks DuckDuckGo HTML, use a network that allows `duckduckgo.com`.
- Some platforms heavily throttle scraping; for production use, prefer official APIs.

## Notes on scale

For a production-grade system, add:

1. Queue + workers (Celery/RQ).
2. Per-source adapters with official APIs where available.
3. Browser automation fallback (Playwright) only when legally permissible.
4. Deduplication and entity resolution.
5. Persistent storage (Postgres + full-text index).
6. Rate limiting, retries, and audit logging.

## Legal + compliance

- Prefer official APIs first.
- Respect robots and anti-bot controls.
- Do not bypass authentication or access controls.
- Store only data you are allowed to collect and process.
