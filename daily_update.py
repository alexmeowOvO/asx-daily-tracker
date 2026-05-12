#!/usr/bin/env python3
"""
Daily update script — run by launchd every day at 5:00 PM.

Three steps, in order:
  1. Scrape today's Evening Wrap article (nodriver, bypasses Cloudflare)
  2. Fetch stock prices (yfinance)
  3. Generate Gemini summary (if not already done)

Must run from crawler/ directory:
  cd "/Users/alex/Desktop/personal project/crawler"
  /Users/alex/.venv-cf/bin/python3 daily_update.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

# ── Ensure we're in the crawler directory ────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR))

DATA_DIR = Path("data")
BASE_URL = "https://www.marketindex.com.au"
CATEGORY_URL = f"{BASE_URL}/news/category/market-wraps"
MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2,
    "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Evening Wrap scrape (nodriver)
# ═══════════════════════════════════════════════════════════════════════════════

def _fix_mojibake(text: str) -> str:
    if not text:
        return text
    suspects = ("\xe2\x80\x99", "\xe2\x80\x9c", "\xe2\x80", "\xc2", "\xc3", "\xf0\x9f")
    if not any(s in text for s in suspects):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def parse_article_date(raw_text: str) -> str:
    """Parse 'Mon 11 May 2026, 17:32 AEST' → YYYY-MM-DD."""
    text = raw_text.strip().removeprefix("UPDATED").strip()
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{2,4})", text)
    if m:
        day = int(m.group(1))
        month = MONTH_MAP.get(m.group(2).lower(), 1)
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}-{day:02d}"
    m = re.match(r"(\d{1,2})\s+(\w+)", text)
    if m:
        day = int(m.group(1))
        month = MONTH_MAP.get(m.group(2).lower())
        if month:
            year = 2025 if month > 5 else 2026
            return f"{year:04d}-{month:02d}-{day:02d}"
    return date.today().isoformat()


def _clean_article_content(content: str) -> str:
    if not content:
        return content
    image_pattern = r"\[IMAGE:\d+\]"
    more_match = re.search(r"\+\d+ more\n+", content)
    if more_match:
        content = content[more_match.end():]
    for pat in [r"The S&P/ASX \d+", r"The ASX \d+", r"Australian shares"]:
        match = re.search(pat, content, re.IGNORECASE)
        if match:
            before = content[:match.start()]
            markers_before = re.findall(image_pattern, before)
            content = content[match.start():]
            if markers_before:
                content = "\n\n".join(markers_before) + "\n\n" + content
            break
    author_match = re.search(r"\nABOUT THE AUTHOR\n", content, re.IGNORECASE)
    if author_match:
        content = content[:author_match.start()]
    return content.strip()


async def _extract_content_with_images(tab) -> tuple[str, list[str]]:
    raw = await tab.evaluate("""
    JSON.stringify((() => {
        let el = document.querySelector('.news-content');
        if (!el) {
            const wrappers = [...document.querySelectorAll('[class*="content-wrapper"]')];
            el = wrappers.find(e => e.querySelector('p'));
        }
        if (!el) el = document.querySelector('.full-content');
        if (!el) el = document.querySelector('main');
        if (!el) return [];

        const items = [];
        const blockTags = new Set(['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
                                   'LI', 'BLOCKQUOTE', 'FIGURE', 'UL', 'OL']);
        function walk(el, depth) {
            if (depth > 4) return;
            for (const child of el.children) {
                const imgs = child.nodeName === 'IMG'
                    ? [child]
                    : [...child.querySelectorAll('img')];
                for (const img of imgs)
                    items.push({type: 'img', src: img.getAttribute('src') || '',
                                width: img.getAttribute('width')});
                if (blockTags.has(child.nodeName)) {
                    const text = child.innerText.trim();
                    if (text) items.push({type: 'text', content: text});
                } else if (child.children.length > 0) {
                    walk(child, depth + 1);
                }
            }
        }
        walk(el, 0);
        return items;
    })())
    """)
    items = json.loads(raw)
    parts, images, seen = [], [], set()
    for item in items:
        if item.get("type") == "text":
            parts.append(item["content"])
        elif item.get("type") == "img":
            src, width = item.get("src", ""), item.get("width")
            if not src or src in seen:
                continue
            if src.startswith("/"):
                src = BASE_URL + src
            try:
                if width and int(width) < 100:
                    continue
            except (ValueError, TypeError):
                pass
            for skip in ["avatar", "icon", "logo", "profile", "author"]:
                if skip in src.lower():
                    break
            else:
                parts.append(f"[IMAGE:{len(images)}]")
                images.append(src)
                seen.add(src)
    return "\n\n".join(parts), images


async def _scrape_latest_evening_wrap() -> str | None:
    """Scrape the latest Evening Wrap article using nodriver.
    Skips if the file already exists. Returns the date (YYYY-MM-DD) or None."""
    import nodriver as uc

    print("\n[Step 1] Evening Wrap scrape")
    browser = await uc.start()

    try:
        tab = await browser.get(CATEGORY_URL)
        for _ in range(30):
            await tab.sleep(1)
            if tab.title and tab.title != "New Tab":
                break
        await tab.sleep(6)
        print(f"  Category page: {tab.title}")

        # Find the first evening-wrap article URL
        url = await tab.evaluate("""
        JSON.stringify((() => {
            const links = [...document.querySelectorAll('article a[href*="evening-wrap"]')];
            for (const a of links) {
                const href = a.getAttribute('href');
                if (href && !href.includes('/category/'))
                    return href.startsWith('http') ? href : 'https://www.marketindex.com.au' + href;
            }
            return null;
        })())
        """)
        url = json.loads(url)
        if not url:
            print("  ✗ No evening-wrap article found on category page.")
            return None

        print(f"  Article URL: {url}")

        # Navigate to article
        tab = await browser.get(url)
        for _ in range(30):
            await tab.sleep(1)
            if tab.title and tab.title != "New Tab":
                break
        await tab.sleep(5)

        # Title
        title = await tab.evaluate(
            'document.querySelector("h1")?.innerText?.trim() || "Unknown"'
        )
        title = _fix_mojibake(title)
        print(f"  Title: {title[:80]}...")

        # Date
        raw_date = await tab.evaluate("""
        JSON.stringify((() => {
            const el = document.querySelector('.main-article-header-bottom-bar-left');
            if (el) return el.textContent.trim().split('\\u2219')[0].trim();
            const t = document.querySelector('time');
            if (t) return t.getAttribute('datetime') || t.textContent.trim();
            return '';
        })())
        """)
        article_date_str = parse_article_date(json.loads(raw_date))
        date_slug = article_date_str.replace("-", "")
        print(f"  Date: {article_date_str}")

        # Check if already scraped
        filepath = DATA_DIR / f"evening_wrap_{date_slug}.json"
        if filepath.exists():
            print(f"  → Already exists, skipping. ({filepath})")
            return article_date_str

        # Scrape content
        content, images = await _extract_content_with_images(tab)
        content = _fix_mojibake(content)
        content = _clean_article_content(content)
        print(f"  Content: {len(content)} chars, {len(images)} images")

        # Save
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        article = {
            "title": title,
            "url": url,
            "date": article_date_str,
            "content": content,
            "images": images,
            "scraped_at": datetime.now().isoformat(),
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved {filepath}")

        return article_date_str

    finally:
        browser.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Stock prices (yfinance)
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_stock_prices():
    """Fetch ASX stock prices and personal stocks via yfinance."""
    from scraper_yfinance import YFinanceStockScraper

    print("\n[Step 2] Stock prices (yfinance)")
    scraper = YFinanceStockScraper()
    scraper.scrape_and_save_stocks()
    scraper.scrape_and_save_my_stocks()
    print("  ✓ Stock prices done")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Gemini summary
# ═══════════════════════════════════════════════════════════════════════════════

def _summarize_one(article: dict, date_slug: str, filepath: Path) -> bool:
    """Summarize a single article. Returns True on success, False on skip,
    raises on quota exhaustion."""
    from config import GEMINI_API_KEY, MY_STOCKS

    if article.get("summary"):
        return False  # already has one

    summary = generate_summary(article, GEMINI_API_KEY, MY_STOCKS)
    formatted = format_content(article, GEMINI_API_KEY)
    moves = extract_broker_moves(article)

    save_summary(date_slug, summary, formatted)
    if moves:
        save_broker_moves(article.get("date", date_slug), moves)

    status = f"({len(summary)} chars, {len(moves)} broker moves)" if moves else f"({len(summary)} chars)"
    print(f"    ✓ {status}")
    return True


def _generate_summary(article_date_str: str | None):
    """Summarise today's article (if new) then backfill any missing summaries
    oldest-first until the Gemini daily quota is exhausted."""
    from config import GEMINI_API_KEY, MY_STOCKS
    from summarizer import (
        generate_summary,
        format_content,
        extract_broker_moves,
        save_summary,
        save_broker_moves,
    )

    print("\n[Step 3] Gemini summary + backfill")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIzaSy...L0UE":
        print("  ✗ No valid GEMINI_API_KEY in config.py. Skipping.")
        return

    # ── 3a. Today's article (just scraped in Step 1) ──────────────────────
    if article_date_str:
        date_slug = article_date_str.replace("-", "")
        filepath = DATA_DIR / f"evening_wrap_{date_slug}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                article = json.load(f)
            if article.get("summary"):
                print(f"  Today's article already summarised — skipping.")
            else:
                print(f"  [today] {article['title'][:65]}...")
                try:
                    _summarize_one(article, date_slug, filepath)
                except Exception as e:
                    msg = str(e)
                    if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                        print(f"    ⚠ Quota exhausted on today's article. Stopping.")
                        return
                    print(f"    ✗ Error: {type(e).__name__}: {msg[:120]}")

    # ── 3b. Backfill all missing summaries, oldest-first ──────────────────
    all_files = sorted(DATA_DIR.glob("evening_wrap_*.json"))  # oldest first

    # Collect the ones needing summaries
    queue = []
    for fp in all_files:
        with open(fp, "r", encoding="utf-8") as f:
            art = json.load(f)
        if not art.get("summary"):
            queue.append((fp, art))

    if not queue:
        print("  All articles already have summaries. Nothing to backfill.")
        return

    total = len(queue)
    print(f"  Backfill: {total} articles need summaries")
    done = 0
    skipped = 0

    for idx, (fp, art) in enumerate(queue, 1):
        date_slug = fp.stem.replace("evening_wrap_", "")
        print(f"  [backfill {idx}/{total}] {date_slug} — {art['title'][:60]}...")

        try:
            if _summarize_one(art, date_slug, fp):
                done += 1
        except Exception as e:
            msg = str(e)
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                print(f"    ⚠ Gemini quota exhausted. Processed {done} today, "
                      f"{total - done - skipped} remaining. Will continue tomorrow.")
                break
            print(f"    ✗ Error: {type(e).__name__}: {msg[:120]}")
            skipped += 1
            continue

        if idx < total:
            time.sleep(3)

    print(f"  Backfill session: {done} summarised, {skipped} failed, "
          f"{total - done - skipped} remaining")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"Daily Update — {datetime.now().isoformat(timespec='seconds')}")
    print(f"Working dir: {os.getcwd()}")
    print("=" * 60)

    article_date = None

    # Step 1
    try:
        article_date = asyncio.run(_scrape_latest_evening_wrap())
    except Exception as e:
        print(f"\n[Step 1] FAILED: {type(e).__name__}: {e}")

    # Step 2
    try:
        _fetch_stock_prices()
    except Exception as e:
        print(f"\n[Step 2] FAILED: {type(e).__name__}: {e}")

    # Step 3
    try:
        _generate_summary(article_date)
    except Exception as e:
        print(f"\n[Step 3] FAILED: {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Daily update complete — {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
