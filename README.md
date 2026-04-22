# Global Music Usage Finder (Quick Run)

You only need:
- Python installed
- Command Prompt

## Run in browser (Windows)

Copy/paste exactly:

```bat
cd C:\NewRaLW
start_app.bat
```

Then open:

```text
http://127.0.0.1:8000
```

Type artist/song and click **Search**.

## If `start_app.bat` fails

```bat
cd C:\NewRaLW
run_web_app.bat
```

Then manually open `http://127.0.0.1:8000`.

## Direct CLI (optional)

```bat
cd C:\NewRaLW
run_tracker.bat --artist "Adele" --song "Hello" --engines ddg bing google --max-results 20 --out results.json
```

## Notes
- No API keys required.
- Results depend on search engine availability/network.
- For platform-level guaranteed coverage, official APIs are still better.
