# ASX Daily Tracker

Automated daily pipeline that scrapes the ASX "Evening Wrap" from
[Market Index](https://www.marketindex.com.au/news), pulls stock prices via
yfinance, generates AI summaries with Google Gemini, and publishes everything
to a static React dashboard on GitHub Pages.

Runs unattended every weekday at 5:00 PM via launchd.

## What it does

1. **Scrape** today's Evening Wrap article (nodriver — bypasses Cloudflare Turnstile)
2. **Fetch** stock prices for the ASX 200 watchlist + your personal holdings (yfinance)
3. **Summarize** the article with Gemini (3–5 bullets, portfolio-aware, broker moves extracted)
4. **Sync** all JSON into `frontend/public/data/` and `git push` — GitHub Pages redeploys automatically

The frontend is read-only in production (static JSON files); a local Flask API
(`api.py`) is used in dev mode for editing holdings.

## Repo layout

```
crawler/
├── daily_update.py          ← entry point run by launchd
├── scraper_evening_wrap.py  ← legacy Playwright scraper (kept for reference)
├── scraper_yfinance.py      ← stock price fetcher
├── summarizer.py            ← Gemini summary + broker-move extraction
├── utils.py                 ← shared content cleaners
├── storage.py               ← JSON read/write helpers
├── api.py                   ← Flask dev server (not used in production)
├── config.py                ← API keys + watchlist (gitignored)
├── config.example.py        ← template
├── data/                    ← scraped articles, prices, P&L
└── frontend/                ← React + TypeScript + Vite + Tailwind
    └── public/data/         ← mirrored from data/ for static deploy
```

## Running it

**Daily run (what launchd executes):**

```bash
cd "/Users/alex/Desktop/personal project/crawler"
/Users/alex/.venv-cf/bin/python3 daily_update.py
```

Output goes to `logs/daily_update.log` (stdout) and `logs/daily_update.err` (stderr).

**Backfilling missing articles:**

Use `~/backfill_evening_wrap.py`. Edit the `CUTOFF` and `END` date constants at
the top, then run from inside the crawler directory:

```bash
cd "/Users/alex/Desktop/personal project/crawler"
/Users/alex/.venv-cf/bin/python3 ~/backfill_evening_wrap.py
```

Already-saved files are skipped, so it's safe to re-run.

**Dev frontend:**

```bash
cd frontend
npm install
npm run dev          # local dev with Flask API
npm run build        # production build → dist/
```

## Failure handling

If any step in `daily_update.py` fails, it:

- writes `logs/LAST_FAILED` with a timestamp and traceback
- fires a macOS notification ("ASX Tracker FAILED")
- clears the marker file on the next clean run

So `[ -e logs/LAST_FAILED ]` tells you at a glance whether the last scheduled
run worked.

For complete coverage of import-time crashes (which happen before the script's
own try/except can run), check `logs/daily_update.err` — non-empty content
means the most recent launchd invocation crashed before `main()` started.

## Python environment

There are two venvs:

- **`~/.venv-cf/`** — used by launchd and the backfill script. Has `nodriver`,
  `yfinance`, `google-genai`. **No `playwright`.**
- **`crawler/.venv/`** — dev venv. Has everything including `playwright` for
  the legacy scraper.

Anything imported by `daily_update.py` (transitively!) must work under
`.venv-cf`. The legacy `scraper_evening_wrap.py` does a lazy `playwright`
import for exactly this reason — don't add eager imports of optional
dependencies to modules that the daily pipeline touches.

## Deployment

GitHub Pages serves the `frontend/dist/` build. The data files in
`frontend/public/data/` are kept in sync with `data/` by `_sync_public_data()`,
which runs at the end of every `daily_update.py` invocation and then
`git add && git commit && git push`. That push triggers the GitHub Pages
deploy workflow.

Live site: https://alexmeowovo.github.io/asx-daily-tracker/

## Config

Copy `config.example.py` to `config.py` and fill in:

- `GEMINI_API_KEY` — get one at https://aistudio.google.com/apikey
- `STOCK_SYMBOLS` — the ASX 200 watchlist on the dashboard
- `MY_STOCKS` — your personal holdings (the "My Portfolio" section in summaries
  only triggers if any of these are mentioned in the article)
