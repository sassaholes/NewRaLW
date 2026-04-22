#!/usr/bin/env python3
"""Local CLI to discover artist/song usage mentions across global web markets.

Supports no-key search across DuckDuckGo, Bing, and Google.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

ENGINE_URLS = {
    "ddg": "https://duckduckgo.com/html/?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}&hl=en",
}


@dataclass
class Mention:
    platform: str
    url: str
    title: str
    snippet: str
    matched_query: str
    engine: str


@dataclass
class SearchDiagnostics:
    attempted_queries: int
    failed_queries: int
    last_error: str = ""


class SearchFailedError(RuntimeError):
    """Raised when every upstream search request fails."""


def build_queries(artist: str | None, song: str | None, markets: list[str]) -> list[str]:
    base_bits = [bit for bit in [artist, song] if bit]
    if not base_bits:
        raise ValueError("You must provide --artist and/or --song")

    base = " ".join(base_bits)
    queries: list[str] = [base]

    usage_terms = ["used in video", "sound trend", "viral clip", "背景音乐", "使用", "热门配乐"]
    queries.extend([f"{base} {term}" for term in usage_terms])

    if "douyin" in markets:
        queries.extend([f'site:douyin.com "{base}"', f'douyin "{base}" 音乐', f'douyin "{base}" 使用'])
    if "tiktok" in markets:
        queries.extend([f'site:tiktok.com "{base}"', f'tiktok "{base}" sound'])
    if "youtube" in markets:
        queries.extend([f'site:youtube.com "{base}"', f'youtube shorts "{base}"'])

    return dedupe_keep_order(queries)


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def detect_platform(url: str) -> str:
    normalized = url.lower()
    if "douyin.com" in normalized:
        return "douyin"
    if "tiktok.com" in normalized:
        return "tiktok"
    if "youtube.com" in normalized or "youtu.be" in normalized:
        return "youtube"
    if "instagram.com" in normalized:
        return "instagram"
    if "x.com" in normalized or "twitter.com" in normalized:
        return "x"
    return "web"


def clean_text(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_google_link(link: str) -> str:
    if link.startswith("/url?"):
        parsed = parse_qs(urlparse(link).query)
        target = parsed.get("q")
        if target and target[0].startswith("http"):
            return target[0]
    return link


def is_valid_result_url(link: str) -> bool:
    if not link:
        return False
    if link.startswith("/"):
        return False
    if "google.com/search" in link or "accounts.google.com" in link:
        return False
    return link.startswith("http")


def fetch_html(url: str, timeout: int = 12) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


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
    snippet_pattern = re.compile(
        r'(?:class="[^"]*result__snippet[^"]*"|data-result-snippet="1")[^>]*>(?P<snippet>.*?)</(?:a|div|span)>',
        re.IGNORECASE | re.DOTALL,
    )

    anchors = list(anchor_pattern.finditer(page_html))
    snippets = list(snippet_pattern.finditer(page_html))

    for idx, match in enumerate(anchors):
        link = unwrap_ddg_redirect(html.unescape(match.group("href")))
        title = clean_text(match.group("title"))
        snippet = clean_text(snippets[idx].group("snippet")) if idx < len(snippets) else ""

        if is_valid_result_url(link):
            mentions.append(
                Mention(
                    platform=detect_platform(link),
                    url=link,
                    title=title,
                    snippet=snippet,
                    matched_query=query,
                    engine="ddg",
                )
            )
    return mentions


def parse_bing_results(page_html: str, query: str) -> list[Mention]:
    mentions: list[Mention] = []
    pattern = re.compile(
        r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>.*?<h2>\s*<a[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>\s*</h2>.*?(?:<p>(?P<snippet>.*?)</p>)?',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        link = html.unescape(match.group("href"))
        if not is_valid_result_url(link):
            continue
        mentions.append(
            Mention(
                platform=detect_platform(link),
                url=link,
                title=clean_text(match.group("title") or ""),
                snippet=clean_text(match.group("snippet") or ""),
                matched_query=query,
                engine="bing",
            )
        )
    return mentions


def parse_google_results(page_html: str, query: str) -> list[Mention]:
    mentions: list[Mention] = []
    pattern = re.compile(
        r'<a[^>]*href="(?P<href>/url\?[^"]+|https?://[^"]+)"[^>]*><h3[^>]*>(?P<title>.*?)</h3></a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        link = normalize_google_link(html.unescape(match.group("href")))
        if not is_valid_result_url(link):
            continue
        mentions.append(
            Mention(
                platform=detect_platform(link),
                url=link,
                title=clean_text(match.group("title") or ""),
                snippet="",
                matched_query=query,
                engine="google",
            )
        )
    return mentions


def search_engine(query: str, engine: str, timeout: int = 12) -> list[Mention]:
    page_html = fetch_html(ENGINE_URLS[engine].format(query=quote_plus(query)), timeout=timeout)
    if engine == "ddg":
        return parse_ddg_results(page_html, query)
    if engine == "bing":
        return parse_bing_results(page_html, query)
    if engine == "google":
        return parse_google_results(page_html, query)
    return []


def run_search(
    artist: Optional[str],
    song: Optional[str],
    markets: list[str],
    timeout: int,
    engines: list[str],
) -> list[Mention]:
    queries = build_queries(artist, song, markets)
    if max_queries is not None:
        queries = queries[: max(max_queries, 0)]
    all_mentions: list[Mention] = []

    for q in queries:
        for engine in engines:
            try:
                all_mentions.extend(search_engine(q, engine=engine, timeout=timeout))
            except (URLError, HTTPError, TimeoutError, KeyError):
                continue
    max_queries: int | None = None,
) -> tuple[list[Mention], SearchDiagnostics]:
    engines = engines or ["ddg", "bing", "google"]
    queries = build_queries(artist, song, markets)
    if max_queries is not None:
        queries = queries[: max(max_queries, 0)]

    all_mentions: list[Mention] = []
    attempts = 0
    failures = 0
    last_error = ""

    for query in queries:
        for engine in engines:
            attempts += 1
            try:
                all_mentions.extend(search_engine(query, engine=engine, timeout=timeout))
            except (URLError, HTTPError, TimeoutError, KeyError) as exc:
                failures += 1
                last_error = str(exc)

    diagnostics = SearchDiagnostics(
        attempted_queries=attempts,
        failed_queries=failures,
        last_error=last_error,
    )

    if attempts and failures == attempts:
        raise SearchFailedError(
            "All search requests failed. This usually means your network, proxy, or firewall blocked requests. "
            f"Last error: {last_error or 'unknown error'}"
        )

    seen: set[str] = set()
    deduped: list[Mention] = []
    for mention in all_mentions:
        if mention.url in seen:
            continue
        seen.add(mention.url)
        deduped.append(mention)

    return deduped, diagnostics


def write_json(path: str, rows: list[Mention]) -> None:
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump([asdict(row) for row in rows], file_handle, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: list[Mention]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["engine", "platform", "url", "title", "snippet", "matched_query"],
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
    parser.add_argument(
        "--engines",
        nargs="+",
        default=["ddg", "bing", "google"],
        choices=["ddg", "bing", "google"],
        help="Search engines to use",
    )
    parser.add_argument("--max-results", type=int, default=50, help="Max result rows to keep")
    parser.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Limit how many generated queries are executed (default: all)",
    )
    parser.add_argument("--timeout", type=int, default=12, help="HTTP timeout (seconds)")
    parser.add_argument("--out", type=str, default=None, help="Path to write JSON")
    parser.add_argument("--csv", type=str, default=None, help="Path to write CSV")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    try:
        rows, diagnostics = run_search(
            args.artist,
            args.song,
            args.markets,
            timeout=args.timeout,
            engines=args.engines,
        )
    except SearchFailedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    rows = rows[: max(args.max_results, 0)]
    print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))

    if diagnostics.failed_queries:
        print(
            f"\nWarning: {diagnostics.failed_queries}/{diagnostics.attempted_queries} requests failed. "
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
