#!/usr/bin/env python3
"""
Backfill summarizer — runs Gemini summarization on all evening-wrap articles
missing a "summary" field. Handles free-tier rate limits with retries.

Must run from the crawler/ directory:
  cd "/Users/alex/Desktop/personal project/crawler"
  python3 summarize_backfill.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from config import GEMINI_API_KEY, MY_STOCKS
from summarizer import (
    generate_summary,
    format_content,
    extract_broker_moves,
    save_summary,
    save_broker_moves,
)

DATA_DIR = Path("data")
DELAY = 3  # seconds between articles
MAX_RETRIES = 3
FREE_TIER_LIMIT = 20  # requests per day (2 per article = 10 articles/day)


def _call_with_retry(fn, *args, name="API", **kwargs) -> str:
    """Call an API function with retry on rate-limit errors."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            last_error = e

            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                # Parse retry delay from error
                delay = 30  # default
                m = re.search(r"retryDelay.*?(\d+)s", msg)
                if m:
                    delay = int(m.group(1)) + 2

                if "per day" in msg or "PerDay" in msg:
                    print(f"  ⚠ Daily quota exhausted ({msg[:200]}...)")
                    raise  # don't retry — quota won't reset until tomorrow

                print(f"  ⚠ Rate limited, waiting {delay}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(delay)
                continue

            raise  # non-rate-limit error, propagate

    raise last_error


def main():
    files = sorted(DATA_DIR.glob("evening_wrap_*.json"))
    total = len(files)
    print(f"Found {total} evening-wrap files in {DATA_DIR.resolve()}")

    needs_summary = []
    already_has = 0

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            article = json.load(f)
        if article.get("summary"):
            already_has += 1
        else:
            needs_summary.append((fp, article))

    print(f"  Already summarized: {already_has}")
    print(f"  Needs summary:      {len(needs_summary)}")
    print(f"  ⚠ Free tier allows ~{FREE_TIER_LIMIT // 2} articles/day (2 calls each)")
    print(f"  ⚠ Will process ~{FREE_TIER_LIMIT // 2} articles, save progress, then stop")
    print(f"  ⚠ Re-run tomorrow to continue from where it stopped")
    print()

    if not needs_summary:
        print("Nothing to do!")
        return

    print("=" * 60)
    api_calls_today = 0
    summarised = 0
    failed = 0
    broker_dates = 0
    quota_exhausted = False

    for idx, (fp, article) in enumerate(needs_summary, 1):
        date_str = fp.stem.replace("evening_wrap_", "")
        print(f"\n[{idx}/{len(needs_summary)}] {date_str} — {article['title'][:65]}...")

        try:
            summary = _call_with_retry(
                generate_summary, article, GEMINI_API_KEY, MY_STOCKS,
                name="summary"
            )
            api_calls_today += 1
            print(f"  ✓ summary ({len(summary)} chars)")

            formatted = _call_with_retry(
                format_content, article, GEMINI_API_KEY,
                name="format"
            )
            api_calls_today += 1
            print(f"  ✓ formatted ({len(formatted)} chars)")

            moves = extract_broker_moves(article)
            if moves:
                print(f"  ✓ broker moves ({len(moves)} entries)")
            else:
                print(f"  - no broker moves")

            save_summary(date_str, summary, formatted)
            if moves:
                save_broker_moves(article.get("date", date_str), moves)
                broker_dates += 1

            summarised += 1

        except Exception as e:
            msg = str(e)
            if "PerDay" in msg or "Daily quota" in str(e):
                print(f"  ✗ Daily quota hit. Stopping for today.")
                quota_exhausted = True
                break
            print(f"  ✗ FAILED: {type(e).__name__}: {str(e)[:120]}")
            failed += 1

        # Rate-limit delay
        if idx < len(needs_summary) and not quota_exhausted:
            time.sleep(DELAY)

    print(f"\n{'=' * 60}")
    print(f"SESSION COMPLETE")
    print(f"  Summarised today: {summarised}")
    print(f"  Failed:           {failed}")
    print(f"  Broker moves:     {broker_dates}")
    print(f"  Already had:      {already_has}")
    print(f"  API calls today:  {api_calls_today}")
    print(f"  Still needed:     ~{len(needs_summary) - summarised - failed}")
    print(f"{'=' * 60}")

    if quota_exhausted or (api_calls_today >= FREE_TIER_LIMIT * 0.9):
        print(f"\nDaily quota nearly/fully used. Re-run tomorrow to continue.")


if __name__ == "__main__":
    main()
