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

## If you see syntax/indent errors

That means your local files are old or corrupted.

1) Re-download latest ZIP from GitHub and extract fresh folder.
2) In Command Prompt, run:

```bat
cd C:\NewRaLW
run_web_app.bat
```

The script now pre-checks Python compile before launch and will stop with a clear message if files are broken.

