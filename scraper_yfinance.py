"""
Stock scraper using yfinance library - much more reliable than web scraping.
"""

from datetime import datetime
from typing import List, Dict, Any
import yfinance as yf

from models import Stock
from storage import (
    save_stocks_json,
    save_stock_history_json,
    save_my_stocks_json,
    save_my_stocks_history_json,
    save_daily_pnl,
    get_my_holdings,
)


class YFinanceStockScraper:
    """Scrapes ASX stock data using yfinance library."""

    def fetch_stock_history(self, symbol: str, days: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch last N trading day closing prices for a stock.

        Args:
            symbol: Stock symbol (e.g., 'CBA.AX')
            days: Number of trading days to return

        Returns:
            List of {date, close} dicts ordered oldest -> newest
        """
        try:
            ticker = yf.Ticker(symbol)
            # Pull extra days to cover non-trading days/weekends
            hist = ticker.history(period="20d", interval="1d")
            if hist.empty or "Close" not in hist:
                return []

            closes = hist["Close"].dropna()
            if closes.empty:
                return []

            closes = closes.tail(days)
            history = []
            for idx, value in closes.items():
                date_str = idx.date().isoformat()
                history.append({"date": date_str, "close": float(value)})

            return history
        except Exception as e:
            print(f"    Error fetching history for {symbol}: {e}")
            return []

    def scrape_stock(self, symbol: str) -> Stock:
        """
        Scrape a single stock using yfinance.

        Args:
            symbol: Stock symbol (e.g., 'CBA.AX')

        Returns:
            Stock object with scraped data
        """
        print(f"  Fetching {symbol}...")

        try:
            # Get stock data from yfinance
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Extract data
            name = info.get('longName', symbol)
            price = info.get('currentPrice', info.get('regularMarketPrice', 0.0))
            previous_close = info.get('previousClose', price)

            # Calculate change
            change = price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0.0

            stock = Stock(
                symbol=symbol,
                name=name,
                price=price,
                change=change,
                change_percent=change_percent,
                timestamp=datetime.now().isoformat(),
                source_url=f"https://finance.yahoo.com/quote/{symbol}",
            )

            print(f"    [OK] {symbol}: {name} - ${price:.2f} ({change:+.2f}, {change_percent:+.2f}%)")
            return stock

        except Exception as e:
            print(f"    Error fetching {symbol}: {e}")
            # Return placeholder if scraping fails
            return Stock(
                symbol=symbol,
                name=symbol,
                price=0.0,
                change=0.0,
                change_percent=0.0,
                timestamp=datetime.now().isoformat(),
                source_url=f"https://finance.yahoo.com/quote/{symbol}",
            )

    def scrape_and_save_stocks(self, symbols: List[str] = None) -> dict:
        """
        Scrape ASX stocks using yfinance and save to JSON.

        Args:
            symbols: List of stock symbols (uses config if None)

        Returns:
            Dictionary with statistics
        """
        if symbols is None:
            from config import STOCK_SYMBOLS
            symbols = STOCK_SYMBOLS

        stats = {
            'stocks_requested': len(symbols),
            'stocks_found': 0,
            'stocks_saved': 0,
        }

        stocks = []
        histories = []

        print(f"\nFetching {len(symbols)} stocks using yfinance...")

        # Scrape each stock
        for symbol in symbols:
            try:
                stock = self.scrape_stock(symbol)
                if stock.price > 0:  # Only add if we got valid data
                    stocks.append(stock)

                history = self.fetch_stock_history(symbol, days=10)
                if history:
                    histories.append({"symbol": symbol, "history": history})
            except Exception as e:
                print(f"  Failed to fetch {symbol}: {e}")
                continue

        stats['stocks_found'] = len(stocks)

        # Save to JSON
        if stocks:
            saved = save_stocks_json(stocks)
            stats['stocks_saved'] = saved

        if histories:
            save_stock_history_json(histories, days=10)

        return stats

    def scrape_and_save_my_stocks(self, symbols: List[str] = None) -> dict:
        """
        Scrape personal stocks using yfinance and save to JSON.

        Args:
            symbols: List of stock symbols (uses config MY_STOCKS if None)

        Returns:
            Dictionary with statistics
        """
        if symbols is None:
            from config import MY_STOCKS
            symbols = MY_STOCKS

        if not symbols:
            print("\nNo MY_STOCKS configured. Skipping.")
            return {'stocks_requested': 0, 'stocks_found': 0, 'stocks_saved': 0}

        stats = {
            'stocks_requested': len(symbols),
            'stocks_found': 0,
            'stocks_saved': 0,
        }

        stocks = []
        histories = []

        print(f"\nFetching {len(symbols)} personal stocks using yfinance...")

        for symbol in symbols:
            try:
                stock = self.scrape_stock(symbol)
                if stock.price > 0:
                    stocks.append(stock)

                history = self.fetch_stock_history(symbol, days=10)
                if history:
                    histories.append({"symbol": symbol, "history": history})
            except Exception as e:
                print(f"  Failed to fetch {symbol}: {e}")
                continue

        stats['stocks_found'] = len(stocks)

        if stocks:
            saved = save_my_stocks_json(stocks)
            stats['stocks_saved'] = saved

        if histories:
            save_my_stocks_history_json(histories, days=10)

        # Calculate and save daily P&L
        self._save_daily_pnl(stocks, histories)

        return stats

    def _save_daily_pnl(self, stocks: list, histories: list):
        """Calculate and save daily P&L based on current holdings using historical data."""
        holdings_data = get_my_holdings()
        holdings = holdings_data.get("holdings", {})

        if not holdings:
            print("  No holdings configured, skipping P&L calculation")
            return

        # Build a map of symbol -> history for easy lookup
        history_map = {}
        trading_date = None
        for h in histories:
            symbol = h.get("symbol")
            history = h.get("history", [])
            if history:
                history_map[symbol] = history
                if not trading_date:
                    trading_date = history[-1]["date"]

        if not trading_date:
            print("  No trading date found, skipping P&L calculation")
            return

        # Calculate total P&L using historical close prices (not current change)
        total_pnl = 0.0
        for stock in stocks:
            shares = holdings.get(stock.symbol, 0)
            if shares > 0:
                # Get the change from history (last day close - second to last day close)
                history = history_map.get(stock.symbol, [])
                if len(history) >= 2:
                    today_close = history[-1]["close"]
                    yesterday_close = history[-2]["close"]
                    change = today_close - yesterday_close
                else:
                    # Fallback to current stock change if not enough history
                    change = stock.change

                pnl = shares * change
                total_pnl += pnl
                print(f"    {stock.symbol}: {shares} shares × ${change:.2f} = ${pnl:.2f}")

        # Save the P&L with holdings snapshot
        save_daily_pnl(trading_date, total_pnl, holdings)
        print(f"  [OK] Saved daily P&L for {trading_date}: ${total_pnl:.2f}")


if __name__ == "__main__":
    scraper = YFinanceStockScraper()
    scraper.scrape_and_save_stocks()
    scraper.scrape_and_save_my_stocks()
