"""
View Stocks Utility

Display the latest stock data from JSON storage.
"""

import json
import os
from datetime import datetime

from config import STOCKS_JSON
from storage import get_latest_stocks


def format_price(value: float) -> str:
    """Format price with dollar sign and 2 decimals."""
    return f"${value:.2f}"


def format_change(value: float) -> str:
    """Format change with + or - sign."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}"


def format_percent(value: float) -> str:
    """Format percentage with + or - sign."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def view_stocks():
    """Display latest stock data from JSON."""

    if not os.path.exists(STOCKS_JSON):
        print("No stock data found. Run main.py or scheduler.py first.")
        return

    data = get_latest_stocks()

    if not data["stocks"]:
        print("No stock data available.")
        return

    # Parse and format last updated time
    last_updated = data["last_updated"]
    if last_updated:
        dt = datetime.fromisoformat(last_updated)
        last_updated_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_updated_str = "Unknown"

    # Display header
    print("\n" + "=" * 80)
    print(f"ASX Stock Prices - Last Updated: {last_updated_str}")
    print("=" * 80)
    print(f"{'Symbol':<10} {'Name':<25} {'Price':>12} {'Change':>12} {'%':>10}")
    print("-" * 80)

    # Display each stock
    for stock in data["stocks"]:
        symbol = stock["symbol"]
        name = stock["name"][:25]  # Truncate long names
        price = format_price(stock["price"])
        change = format_change(stock["change"])
        change_pct = format_percent(stock["change_percent"])

        print(f"{symbol:<10} {name:<25} {price:>12} {change:>12} {change_pct:>10}")

    print("=" * 80)
    print(f"Total stocks: {data['count']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    view_stocks()
