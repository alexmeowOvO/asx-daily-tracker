"""
ASX Stock Scraper - Main Entry Point

This script provides manual scraping functionality for ASX stocks.
For automated daily scraping at 5 PM, use scheduler.py instead.

Architecture:
- config.py: ASX URLs and stock symbols
- models.py: Stock data models
- fetcher.py: Playwright browser management
- scraper.py: ASX stock scraping logic
- storage.py: JSON file storage
"""

from config import STOCK_SYMBOLS
from scraper_yfinance import YFinanceStockScraper


def main():
    """Main entry point for manual stock scraping."""

    print("ASX Stock Scraper")
    print("=" * 60)
    print(f"Tracking {len(STOCK_SYMBOLS)} stocks: {', '.join(STOCK_SYMBOLS)}")
    print("=" * 60)

    # Create scraper and run
    scraper = YFinanceStockScraper()
    stats = scraper.scrape_and_save_stocks()

    # Print summary
    print(f"\n{'='*60}")
    print("Scraping Complete")
    print(f"{'='*60}")
    print(f"Stocks requested: {stats['stocks_requested']}")
    print(f"Stocks found:     {stats['stocks_found']}")
    print(f"Stocks saved:     {stats['stocks_saved']}")
    print(f"{'='*60}")
    print("\nData saved to:")
    print("  - data/stocks.json (latest)")
    print("  - data/history/ (historical archive)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
