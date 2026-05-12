import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any

try:
    import db  # Legacy MySQL support (optional)
except ImportError:
    db = None
from models import Quote, Stock


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    from config import DATA_DIR, HISTORY_DIR

    Path(DATA_DIR).mkdir(exist_ok=True)
    Path(HISTORY_DIR).mkdir(exist_ok=True)


def save_stocks_json(stocks: List[Stock]) -> int:
    """
    Save stocks to JSON file.

    Args:
        stocks: List of Stock objects

    Returns:
        Number of stocks saved
    """
    from config import STOCKS_JSON

    if not stocks:
        return 0

    ensure_data_dirs()

    # Convert stocks to dictionaries
    data = {
        "last_updated": datetime.now().isoformat(),
        "stocks": [stock.to_dict() for stock in stocks],
        "count": len(stocks),
    }

    # Save to JSON file
    with open(STOCKS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Also save to history with timestamp
    from config import HISTORY_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = f"{HISTORY_DIR}/stocks_{timestamp}.json"

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(stocks)} stocks to {STOCKS_JSON}")
    print(f"[OK] Archived to {history_file}")

    return len(stocks)


def load_stocks_json() -> List[Stock]:
    """
    Load stocks from JSON file.

    Returns:
        List of Stock objects, empty list if file doesn't exist
    """
    from config import STOCKS_JSON

    if not os.path.exists(STOCKS_JSON):
        return []

    with open(STOCKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    stocks = [Stock.from_dict(stock_data) for stock_data in data.get("stocks", [])]
    return stocks


def get_latest_stocks() -> dict:
    """
    Get latest stock data with metadata.

    Returns:
        Dictionary with last_updated, stocks, and count
    """
    from config import STOCKS_JSON

    if not os.path.exists(STOCKS_JSON):
        return {"last_updated": None, "stocks": [], "count": 0}

    with open(STOCKS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_stock_history_json(history: List[Dict[str, Any]], days: int = 10) -> int:
    """
    Save stock price history to JSON file.

    Args:
        history: List of history items with symbol and history array
        days: Number of trading days included

    Returns:
        Number of stocks saved
    """
    from config import STOCKS_HISTORY_JSON

    if not history:
        return 0

    ensure_data_dirs()

    data = {
        "last_updated": datetime.now().isoformat(),
        "days": days,
        "stocks": history,
        "count": len(history),
    }

    with open(STOCKS_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(history)} stock histories to {STOCKS_HISTORY_JSON}")
    return len(history)


def get_latest_stock_history() -> dict:
    """
    Get latest stock history data with metadata.

    Returns:
        Dictionary with last_updated, days, stocks array, and count
    """
    from config import STOCKS_HISTORY_JSON

    if not os.path.exists(STOCKS_HISTORY_JSON):
        return {"last_updated": None, "days": 10, "stocks": [], "count": 0}

    with open(STOCKS_HISTORY_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_my_stocks_json(stocks: List[Stock]) -> int:
    """Save my personal stocks to JSON file."""
    from config import MY_STOCKS_JSON

    if not stocks:
        return 0

    ensure_data_dirs()

    data = {
        "last_updated": datetime.now().isoformat(),
        "stocks": [stock.to_dict() for stock in stocks],
        "count": len(stocks),
    }

    with open(MY_STOCKS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(stocks)} my stocks to {MY_STOCKS_JSON}")
    return len(stocks)


def get_my_stocks() -> dict:
    """Get my personal stocks data."""
    from config import MY_STOCKS_JSON

    if not os.path.exists(MY_STOCKS_JSON):
        return {"last_updated": None, "stocks": [], "count": 0}

    with open(MY_STOCKS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_my_stocks_history_json(history: List[Dict[str, Any]], days: int = 10) -> int:
    """Save my stocks price history to JSON file."""
    from config import MY_STOCKS_HISTORY_JSON

    if not history:
        return 0

    ensure_data_dirs()

    data = {
        "last_updated": datetime.now().isoformat(),
        "days": days,
        "stocks": history,
        "count": len(history),
    }

    with open(MY_STOCKS_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(history)} my stock histories to {MY_STOCKS_HISTORY_JSON}")
    return len(history)


def get_my_stocks_history() -> dict:
    """Get my stocks history data."""
    from config import MY_STOCKS_HISTORY_JSON

    if not os.path.exists(MY_STOCKS_HISTORY_JSON):
        return {"last_updated": None, "days": 10, "stocks": [], "count": 0}

    with open(MY_STOCKS_HISTORY_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_my_holdings(holdings: Dict[str, int], purchase_prices: Dict[str, float] = None) -> bool:
    """Save my stock holdings and purchase prices to JSON file."""
    from config import MY_HOLDINGS_JSON

    ensure_data_dirs()

    # Load existing data to preserve purchase_prices if not provided
    existing = get_my_holdings()

    data = {
        "last_updated": datetime.now().isoformat(),
        "holdings": holdings,
        "purchase_prices": purchase_prices if purchase_prices is not None else existing.get("purchase_prices", {}),
    }

    with open(MY_HOLDINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return True


def get_my_holdings() -> dict:
    """Get my stock holdings and purchase prices data."""
    from config import MY_HOLDINGS_JSON

    if not os.path.exists(MY_HOLDINGS_JSON):
        return {"last_updated": None, "holdings": {}, "purchase_prices": {}}

    with open(MY_HOLDINGS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Ensure purchase_prices exists for backward compatibility
    if "purchase_prices" not in data:
        data["purchase_prices"] = {}

    return data


def save_daily_pnl(date: str, pnl: float, holdings_snapshot: Dict[str, int]) -> bool:
    """
    Save daily P&L for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format
        pnl: Total P&L for the day
        holdings_snapshot: Snapshot of holdings used for calculation
    """
    from config import DAILY_PNL_JSON

    ensure_data_dirs()

    # Load existing data
    data = get_daily_pnl()

    # Add or update this date's P&L
    data["records"][date] = {
        "pnl": pnl,
        "holdings": holdings_snapshot,
        "calculated_at": datetime.now().isoformat(),
    }
    data["last_updated"] = datetime.now().isoformat()

    with open(DAILY_PNL_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return True


def get_daily_pnl() -> dict:
    """Get all daily P&L records."""
    from config import DAILY_PNL_JSON

    if not os.path.exists(DAILY_PNL_JSON):
        return {"last_updated": None, "records": {}}

    with open(DAILY_PNL_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# Legacy function - save quotes to MySQL database
def save_quotes(quotes: Iterable[Quote]) -> int:
    """Save quotes to MySQL database (legacy support)."""
    quotes_list = list(quotes)
    if not quotes_list:
        return 0

    rows = [q.as_row() for q in quotes_list]
    if db is not None:
        db.insert_quotes(rows)
    return len(quotes_list)
