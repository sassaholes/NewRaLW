#!/usr/bin/env python3
"""Tiny local web app for Global Music Usage Finder.

Run:
  python web_app.py
Then open http://127.0.0.1:8000 in your browser.
"""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from tracker import Mention, run_search

HOST = "127.0.0.1"
PORT = 8000


def render_page(rows: list[Mention] | None = None, error: str = "", form: dict[str, str] | None = None) -> bytes:
    rows = rows or []
    form = form or {}

    artist = html.escape(form.get("artist", ""))
    song = html.escape(form.get("song", ""))
    max_results = html.escape(form.get("max_results", "20"))
    timeout = html.escape(form.get("timeout", "12"))

    table_rows = ""
    for r in rows:
        table_rows += (
            "<tr>"
            f"<td>{html.escape(r.platform)}</td>"
            f"<td><a href='{html.escape(r.url)}' target='_blank'>link</a></td>"
            f"<td>{html.escape(r.title)}</td>"
            f"<td>{html.escape(r.snippet)}</td>"
            "</tr>"
        )

    error_html = f"<p class='error'>{html.escape(error)}</p>" if error else ""
    results_header = f"<p><strong>{len(rows)}</strong> result(s).</p>" if rows else ""

    page = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Music Usage Finder</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 1100px; margin: 24px auto; padding: 0 12px; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; }}
    input, select {{ padding: 8px; margin: 4px; }}
    button {{ padding: 8px 12px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f5f5f5; }}
    .error {{ color: #b00020; }}
  </style>
</head>
<body>
  <h1>Global Music Usage Finder</h1>
  <p>Search artist/song mentions across global web markets (including Douyin).</p>

  <div class="card">
    <form method="post" action="/search">
      <label>Artist <input name="artist" value="{artist}" placeholder="Adele" /></label>
      <label>Song <input name="song" value="{song}" placeholder="Hello" /></label>
      <label>Max results <input name="max_results" value="{max_results}" size="4" /></label>
      <label>Timeout <input name="timeout" value="{timeout}" size="4" /></label>
      <br />
      <label><input type="checkbox" name="markets" value="global" checked /> Global</label>
      <label><input type="checkbox" name="markets" value="douyin" checked /> Douyin</label>
      <label><input type="checkbox" name="markets" value="tiktok" checked /> TikTok</label>
      <label><input type="checkbox" name="markets" value="youtube" checked /> YouTube</label>
      <br /><br />
      <button type="submit">Search</button>
    </form>
    {error_html}
    {results_header}
  </div>

  <table>
    <thead>
      <tr><th>Platform</th><th>URL</th><th>Title</th><th>Snippet</th></tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""
    return page.encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    def _send_html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = json.dumps({"status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        body = render_page()
        self._send_html(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/search":
            self._send_html(render_page(error="Not found."), status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_html(render_page(error="Invalid content length."), status=400)
            return

        payload = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(payload)

        artist = (form.get("artist") or [""])[0].strip() or None
        song = (form.get("song") or [""])[0].strip() or None

        markets = form.get("markets") or ["global", "douyin", "tiktok", "youtube"]
        max_results_raw = (form.get("max_results") or ["20"])[0]
        timeout_raw = (form.get("timeout") or ["12"])[0]

        view_form = {
            "artist": artist or "",
            "song": song or "",
            "max_results": max_results_raw,
            "timeout": timeout_raw,
        }

        try:
            max_results = max(0, int(max_results_raw))
            timeout = max(1, int(timeout_raw))
            rows = run_search(artist, song, markets, timeout=timeout)[:max_results]
            self._send_html(render_page(rows=rows, form=view_form))
        except ValueError as exc:
            self._send_html(render_page(error=str(exc), form=view_form), status=400)


def main() -> None:
    server = HTTPServer((HOST, PORT), AppHandler)
    print(f"Open http://{HOST}:{PORT} in your browser")
    server.serve_forever()


if __name__ == "__main__":
    main()
