#!/usr/bin/env python3
"""Local CLI to discover artist/song usage mentions across global web markets."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

DUCKDUCKGO_HTML = "https://duckduckgo.com/html/?q={query}"


@dataclass
class Mention:
    platform: str
    url: str
    title: str
    snippet: str
    matched_query: str


@dataclass
class SearchDiagnostics:
    attempted_queries: int
    failed_queries: int
    last_error: str = ""


class SearchFailedError(RuntimeError):
    """Raised when every upstream search request fails."""


def build_queries(artist: str | None, song: str | None, markets: list[str]) -> list[str]:
    base_bits = [b for b in [artist, song] if b]
    if not base_bits:
        raise ValueError("You must provide --artist and/or --song")

    base = " ".join(base_bits)
    queries: list[str] = [base]

    usage_terms = [
        "used in video",
        "sound trend",
        "viral clip",
        "背景音乐",
        "使用",
        "热门配乐",
    ]
    queries.extend([f"{base} {term}" for term in usage_terms])

    if "douyin" in markets:
        queries.extend(
            [
                f'site:douyin.com "{base}"',
                f'douyin "{base}" 音乐',
                f'douyin "{base}" 使用',
            ]
        )
    if "tiktok" in markets:
        queries.extend([f'site:tiktok.com "{base}"', f'tiktok "{base}" sound'])
    if "youtube" in markets:
        queries.extend([f'site:youtube.com "{base}"', f'youtube shorts "{base}"'])

    return dedupe_keep_order(queries)


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        k = item.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def detect_platform(url: str) -> str:
    u = url.lower()
    if "douyin.com" in u:
        return "douyin"
    if "tiktok.com" in u:
        return "tiktok"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "instagram.com" in u:
        return "instagram"
    if "x.com" in u or "twitter.com" in u:
        return "x"
    return "web"


def clean_text(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_html(url: str, timeout: int = 12) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def unwrap_ddg_redirect(url: str) -> str:
    """Extract destination URL from DuckDuckGo redirect links when present."""
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url

    query = parse_qs(parsed.query)
    uddg = query.get("uddg")
    if not uddg:
        return url
    return unquote(uddg[0])


def parse_ddg_results(page_html: str, query: str) -> list[Mention]:
    mentions: list[Mention] = []

    anchor_pattern = re.compile(
        r'<a[^>]*(?:class="[^"]*result__a[^"]*"|data-testid="result-title-a")[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    # Snippets generally appear near anchors in DDG HTML results.
    snippet_pattern = re.compile(
        r'(?:class="[^"]*result__snippet[^"]*"|data-result-snippet="1")[^>]*>(?P<snippet>.*?)</(?:a|div|span)>',
        re.IGNORECASE | re.DOTALL,
    )

    anchors = list(anchor_pattern.finditer(page_html))
    snippets = list(snippet_pattern.finditer(page_html))

    for idx, match in enumerate(anchors):
        link = unwrap_ddg_redirect(html.unescape(match.group("href")))
        title = clean_text(match.group("title"))

        snippet = ""
        if idx < len(snippets):
            snippet = clean_text(snippets[idx].group("snippet") or "")

        mentions.append(
            Mention(
                platform=detect_platform(link),
                url=link,
                title=title,
                snippet=snippet,
                matched_query=query,
            )
        )

    return mentions


def search_ddg(query: str, timeout: int = 12) -> list[Mention]:
    url = DUCKDUCKGO_HTML.format(query=quote_plus(query))
    page_html = fetch_html(url, timeout=timeout)
    return parse_ddg_results(page_html, query)


def run_search(
    artist: str | None,
    song: str | None,
    markets: list[str],
    timeout: int,
    max_queries: int | None = None,
) -> tuple[list[Mention], SearchDiagnostics]:
    queries = build_queries(artist, song, markets)
    if max_queries is not None:
        queries = queries[: max(max_queries, 0)]
    all_mentions: list[Mention] = []

    failed_queries = 0
    last_error = ""

    for q in queries:
        try:
            all_mentions.extend(search_ddg(q, timeout=timeout))
        except (URLError, HTTPError, TimeoutError) as exc:
            failed_queries += 1
            last_error = str(exc)
            continue

    seen: set[str] = set()
    deduped: list[Mention] = []
    for m in all_mentions:
        if m.url in seen:
            continue
        seen.add(m.url)
        deduped.append(m)

    diagnostics = SearchDiagnostics(
        attempted_queries=len(queries),
        failed_queries=failed_queries,
        last_error=last_error,
    )

    if queries and failed_queries == len(queries):
        raise SearchFailedError(
            "All search requests failed. This usually means your network, proxy, or firewall blocked the request. "
            f"Last error: {last_error or 'unknown error'}"
        )

    return deduped, diagnostics


def write_json(path: str, rows: list[Mention]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in rows], f, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: list[Mention]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["platform", "url", "title", "snippet", "matched_query"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find likely artist/song usage mentions globally.")
    parser.add_argument("--artist", type=str, default=None, help="Artist name")
    parser.add_argument("--song", type=str, default=None, help="Song title")
    parser.add_argument(
        "--markets",
        nargs="+",
        default=["global", "douyin", "tiktok", "youtube"],
        choices=["global", "douyin", "tiktok", "youtube"],
        help="Target markets/platforms",
    )
    parser.add_argument("--max-results", type=int, default=50, help="Max result rows to keep")
    parser.add_argument("--timeout", type=int, default=12, help="HTTP timeout (seconds)")
    parser.add_argument("--out", type=str, default=None, help="Path to write JSON")
    parser.add_argument("--csv", type=str, default=None, help="Path to write CSV")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        rows, diagnostics = run_search(args.artist, args.song, args.markets, timeout=args.timeout)
    except SearchFailedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    rows = rows[: max(args.max_results, 0)]

    print(json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2))

    if diagnostics.failed_queries:
        print(
            f"\nWarning: {diagnostics.failed_queries}/{diagnostics.attempted_queries} queries failed. "
            "Results may be incomplete.",
            file=sys.stderr,
        )

    if args.out:
        write_json(args.out, rows)
        print(f"\nSaved JSON: {args.out}")
    if args.csv:
        write_csv(args.csv, rows)
        print(f"Saved CSV: {args.csv}")


if __name__ == "__main__":
    main()
