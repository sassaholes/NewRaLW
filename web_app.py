#!/usr/bin/env python3
"""Tiny local web app for Global Music Usage Finder."""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from tracker import Mention, SearchFailedError, run_search

HOST = "127.0.0.1"
PORT = 8000


def checked(form: dict[str, str], field: str, value: str, default: set[str]) -> str:
    selected = set(filter(None, form.get(field, "").split(",")))
    effective = selected or default
    return "checked" if value in effective else ""


def render_page(rows: list[Mention] | None = None, error: str = "", form: dict[str, str] | None = None) -> bytes:
    rows = rows or []
    form = form or {}

    artist = html.escape(form.get("artist", ""))
    song = html.escape(form.get("song", ""))
    max_results = html.escape(form.get("max_results", "20"))
    timeout = html.escape(form.get("timeout", "12"))

    markets_default = {"global", "douyin", "tiktok", "youtube"}
    engines_default = {"ddg", "bing", "google"}

    table_rows = ""
    for row in rows:
        table_rows += (
            "<tr>"
            f"<td>{html.escape(row.engine)}</td>"
            f"<td>{html.escape(row.platform)}</td>"
            f"<td><a href='{html.escape(row.url)}' target='_blank'>link</a></td>"
            f"<td>{html.escape(row.title)}</td>"
            f"<td>{html.escape(row.snippet)}</td>"
            "</tr>"
        )

    error_html = f"<p class='error'>{html.escape(error)}</p>" if error else ""
    results_header = f"<p><strong>{len(rows)}</strong> result(s).</p>" if rows else ""
    empty_state = (
        "<p>No results yet. Enter artist/song and click Search. "
        "If you keep getting 0 rows, try timeout 10-20 and check your network access.</p>"
        if not rows and not error
        else ""
    )

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
    input {{ padding: 8px; margin: 4px; }}
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
      <label><input type="checkbox" name="markets" value="global" {checked(form, 'markets', 'global', markets_default)} /> Global</label>
      <label><input type="checkbox" name="markets" value="douyin" {checked(form, 'markets', 'douyin', markets_default)} /> Douyin</label>
      <label><input type="checkbox" name="markets" value="tiktok" {checked(form, 'markets', 'tiktok', markets_default)} /> TikTok</label>
      <label><input type="checkbox" name="markets" value="youtube" {checked(form, 'markets', 'youtube', markets_default)} /> YouTube</label>
      <br /><br />
      <strong>Search engines:</strong>
      <label><input type="checkbox" name="engines" value="ddg" {checked(form, 'engines', 'ddg', engines_default)} /> DuckDuckGo</label>
      <label><input type="checkbox" name="engines" value="bing" {checked(form, 'engines', 'bing', engines_default)} /> Bing</label>
      <label><input type="checkbox" name="engines" value="google" {checked(form, 'engines', 'google', engines_default)} /> Google</label>
      <br /><br />
      <button type="submit">Search</button>
    </form>
    {error_html}
    {results_header}
    {empty_state}
  </div>

  <table>
    <thead>
      <tr><th>Engine</th><th>Platform</th><th>URL</th><th>Title</th><th>Snippet</th></tr>
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
        self._send_html(render_page())

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
        form_data = parse_qs(payload)

        artist = (form_data.get("artist") or [""])[0].strip() or None
        song = (form_data.get("song") or [""])[0].strip() or None
        markets = form_data.get("markets") or ["global", "douyin", "tiktok", "youtube"]
        engines = form_data.get("engines") or ["ddg", "bing", "google"]
        max_results_raw = (form_data.get("max_results") or ["20"])[0]
        timeout_raw = (form_data.get("timeout") or ["12"])[0]

        view_form = {
            "artist": artist or "",
            "song": song or "",
            "max_results": max_results_raw,
            "timeout": timeout_raw,
            "markets": ",".join(markets),
            "engines": ",".join(engines),
        }

        try:
            max_results = max(0, int(max_results_raw))
            timeout = max(1, int(timeout_raw))
            rows, diagnostics = run_search(artist, song, markets, timeout=timeout, engines=engines)
            if max_results > 0:
                rows = rows[:max_results]

            warning = ""
            if diagnostics.failed_queries:
                warning = (
                    f"Warning: {diagnostics.failed_queries}/{diagnostics.attempted_queries} requests failed; "
                    "results may be incomplete."
                )
            self._send_html(render_page(rows=rows, form=view_form, error=warning))
        except (ValueError, SearchFailedError) as exc:
            self._send_html(render_page(error=str(exc), form=view_form), status=400)


def main() -> None:
    server = HTTPServer((HOST, PORT), AppHandler)
    print(f"Open http://{HOST}:{PORT} in your browser")
    server.serve_forever()


if __name__ == "__main__":
    main()
