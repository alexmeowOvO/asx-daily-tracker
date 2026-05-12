"""
FastAPI Backend for ASX Stock Tracker Dashboard.

Provides REST API endpoints to serve stock data and evening wrap articles.
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from storage import get_latest_stocks, get_latest_stock_history, get_my_stocks, get_my_stocks_history, get_my_holdings, save_my_holdings, get_daily_pnl

app = FastAPI(
    title="ASX Stock Tracker API",
    description="API for ASX stock prices and Evening Wrap articles",
    version="1.0.0",
)

# CORS middleware for development (Vite runs on port 5173, n8n on 5678)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5678", "http://127.0.0.1:5678"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DATA_DIR = Path("data")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/stocks")
def get_stocks():
    """
    Get latest stock data.

    Returns:
        Dictionary with last_updated, stocks array, and count.
    """
    return get_latest_stocks()


@app.get("/api/stocks-history")
def get_stocks_history():
    """
    Get latest stock history data (last 10 trading days).

    Returns:
        Dictionary with last_updated, days, stocks array, and count.
    """
    return get_latest_stock_history()


@app.get("/api/my-stocks")
def get_my_stocks_endpoint():
    """Get my personal stocks data."""
    return get_my_stocks()


@app.get("/api/my-stocks-history")
def get_my_stocks_history_endpoint():
    """Get my personal stocks history data."""
    return get_my_stocks_history()


@app.get("/api/my-holdings")
def get_my_holdings_endpoint():
    """Get my stock holdings (shares owned)."""
    return get_my_holdings()


@app.post("/api/my-holdings")
def save_my_holdings_endpoint(data: dict):
    """Save my stock holdings and purchase prices."""
    save_my_holdings(
        data.get("holdings", {}),
        data.get("purchase_prices")
    )
    return {"status": "ok"}


@app.get("/api/daily-pnl")
def get_daily_pnl_endpoint():
    """Get all daily P&L records."""
    return get_daily_pnl()


@app.get("/api/evening-wrap")
def get_latest_evening_wrap():
    """
    Get the latest Evening Wrap article.

    Returns:
        Evening wrap article with title, url, date, content, and scraped_at.
    """
    files = sorted(DATA_DIR.glob("evening_wrap_*.json"), reverse=True)

    if not files:
        raise HTTPException(status_code=404, detail="No evening wrap articles found")

    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/evening-wrap/list")
def list_evening_wraps():
    """
    List all available Evening Wrap articles.

    Returns:
        List of articles with date and title.
    """
    files = sorted(DATA_DIR.glob("evening_wrap_*.json"), reverse=True)

    articles = []
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                articles.append({
                    "date": data.get("date"),
                    "title": data.get("title"),
                    "filename": file.name,
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return {"articles": articles, "count": len(articles)}


@app.get("/api/evening-wrap/{date}")
def get_evening_wrap_by_date(date: str):
    """
    Get Evening Wrap article by date.

    Args:
        date: Date in YYYYMMDD format (e.g., 20260130)

    Returns:
        Evening wrap article for the specified date.
    """
    # Try both formats: YYYYMMDD and YYYY-MM-DD
    date_clean = date.replace("-", "")
    filepath = DATA_DIR / f"evening_wrap_{date_clean}.json"

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"No evening wrap found for date: {date}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Automation Endpoints - Trigger scrapers via HTTP
# ============================================================

def run_script(script_name: str, env_vars: dict = None):
    """Run a Python script and return the result."""
    python_exe = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    script_path = Path(__file__).parent / script_name

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_vars:
        env.update(env_vars)

    result = subprocess.run(
        [str(python_exe), str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent),
        env=env,
        timeout=300
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


@app.post("/api/run/stock-scraper")
def run_stock_scraper():
    """Trigger the stock price scraper."""
    try:
        result = run_script("scraper_yfinance.py")
        return result
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Script timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run/evening-wrap-scraper")
def run_evening_wrap_scraper():
    """Trigger the Evening Wrap article scraper."""
    try:
        result = run_script("scraper_evening_wrap.py")
        return result
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Script timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run/summarizer")
def run_summarizer(api_key: str = None):
    """
    Trigger the AI summarizer.

    Args:
        api_key: Optional Gemini API key. If not provided, uses config or env var.
    """
    try:
        env_vars = {}
        if api_key:
            env_vars["GEMINI_API_KEY"] = api_key
        elif not os.environ.get("GEMINI_API_KEY"):
            # Load from config if not in environment
            try:
                from config import GEMINI_API_KEY
                if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
                    env_vars["GEMINI_API_KEY"] = GEMINI_API_KEY
            except ImportError:
                pass
        result = run_script("summarizer.py", env_vars)
        return result
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Script timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run/all")
def run_all_scrapers(api_key: str = None):
    """Run all scrapers in sequence: stocks -> evening wrap -> summarizer."""
    results = {}

    try:
        results["stock_scraper"] = run_script("scraper_yfinance.py")
    except Exception as e:
        results["stock_scraper"] = {"success": False, "error": str(e)}

    try:
        results["evening_wrap_scraper"] = run_script("scraper_evening_wrap.py")
    except Exception as e:
        results["evening_wrap_scraper"] = {"success": False, "error": str(e)}

    try:
        env_vars = {}
        if api_key:
            env_vars["GEMINI_API_KEY"] = api_key
        elif not os.environ.get("GEMINI_API_KEY"):
            # Load from config if not in environment
            try:
                from config import GEMINI_API_KEY
                if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
                    env_vars["GEMINI_API_KEY"] = GEMINI_API_KEY
            except ImportError:
                pass
        results["summarizer"] = run_script("summarizer.py", env_vars)
    except Exception as e:
        results["summarizer"] = {"success": False, "error": str(e)}

    # After scraping, deploy data to frontend for Vercel
    try:
        deploy_result = deploy_data()
        results["deploy"] = deploy_result
    except Exception as e:
        results["deploy"] = {"success": False, "error": str(e)}

    return {
        "success": all(r.get("success", False) for r in results.values()),
        "results": results
    }


@app.post("/api/run/deploy")
def run_deploy():
    """Copy data files to frontend/public/data and push to GitHub."""
    try:
        return deploy_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def deploy_data():
    """Copy data to frontend/public/data, build index, git commit + push."""
    import shutil

    data_dir = Path(__file__).parent / "data"
    public_data = Path(__file__).parent / "frontend" / "public" / "data"
    public_data.mkdir(parents=True, exist_ok=True)

    # Copy data files
    files_to_copy = [
        "stocks.json", "stocks_history_10d.json",
        "my_stocks.json", "my_stocks_history_10d.json",
        "my_holdings.json", "daily_pnl.json",
    ]
    for f in files_to_copy:
        src = data_dir / f
        if src.exists():
            shutil.copy2(str(src), str(public_data / f))

    # Copy evening wrap files
    for src in data_dir.glob("evening_wrap_*.json"):
        shutil.copy2(str(src), str(public_data / src.name))

    # Generate evening wrap index
    import json
    articles = []
    for f in sorted(data_dir.glob("evening_wrap_*.json"), reverse=True):
        with open(f, "r", encoding="utf-8") as fh:
            article = json.load(fh)
            articles.append({
                "date": article.get("date"),
                "title": article.get("title"),
                "filename": f.name,
            })
    with open(public_data / "evening_wrap_index.json", "w", encoding="utf-8") as fh:
        json.dump({"articles": articles, "count": len(articles)}, fh, ensure_ascii=False, indent=2)

    # Git commit and push
    cwd = str(Path(__file__).parent)
    try:
        subprocess.run(["git", "add", "frontend/public/data/"], cwd=cwd, capture_output=True, text=True)
        result = subprocess.run(
            ["git", "commit", "-m", "Update data files"],
            cwd=cwd, capture_output=True, text=True
        )
        push_result = subprocess.run(
            ["git", "push"],
            cwd=cwd, capture_output=True, text=True
        )
        return {
            "success": True,
            "commit": result.stdout or result.stderr,
            "push": push_result.stdout or push_result.stderr,
        }
    except Exception as e:
        return {"success": False, "error": f"Git push failed: {str(e)}"}


# Production: Serve frontend static files
# Uncomment below after building frontend with `npm run build`
# frontend_dir = Path("frontend/dist")
# if frontend_dir.exists():
#     app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
