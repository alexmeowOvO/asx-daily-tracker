import schedule
import time
from datetime import datetime

from config import SCRAPE_TIME, STOCK_SYMBOLS
from scraper_yfinance import YFinanceStockScraper


def scrape_stocks_job():
    """Job function that runs the stock scraping."""
    print(f"\n{'='*60}")
    print(f"Starting scheduled stock scraping at {datetime.now()}")
    print(f"{'='*60}\n")

    scraper = YFinanceStockScraper()
    stats = scraper.scrape_and_save_stocks(STOCK_SYMBOLS)

    print(f"\n{'='*60}")
    print("Scraping Complete")
    print(f"{'='*60}")
    print(f"Stocks requested: {stats['stocks_requested']}")
    print(f"Stocks found:     {stats['stocks_found']}")
    print(f"Stocks saved:     {stats['stocks_saved']}")
    print(f"{'='*60}\n")


def start_scheduler():
    """
    Start the scheduler to run stock scraping daily at 5 PM.

    The scheduler will:
    - Run scraping at SCRAPE_TIME (default 17:00 / 5 PM) every day
    - Keep running indefinitely
    - Can be stopped with Ctrl+C
    """
    print(f"Scheduler started. Will scrape stocks daily at {SCRAPE_TIME}")
    print("Press Ctrl+C to stop\n")

    # Schedule the job
    schedule.every().day.at(SCRAPE_TIME).do(scrape_stocks_job)

    # Run immediately on start (optional - remove if you only want scheduled runs)
    print("Running initial scrape...")
    scrape_stocks_job()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
