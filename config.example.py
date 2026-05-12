# ASX Stock Scraping Configuration via Yahoo Finance
YAHOO_FINANCE_BASE_URL = "https://finance.yahoo.com"

# Stock symbols to track (ASX 200 top stocks)
# Note: Yahoo Finance requires .AX suffix for ASX stocks
STOCK_SYMBOLS = [
    "CBA.AX",  # Commonwealth Bank
    "BHP.AX",  # BHP Group
    "NAB.AX",  # National Australia Bank
    "WBC.AX",  # Westpac Banking
    "ANZ.AX",  # ANZ Banking
    "CSL.AX",  # CSL Limited
    "WES.AX",  # Wesfarmers
    "MQG.AX",  # Macquarie Group
    "WOW.AX",  # Woolworths
    "FMG.AX",  # Fortescue Metals

]

# My personal stocks to track
MY_STOCKS = [
    "ZIP.AX",  # Zip Co
    "APX.AX",  # Appen
    "NVX.AX",  # Novonix
    "DRO.AX",
    # Add your stocks here
]

# Function to get Yahoo Finance URL for a stock
def get_stock_url(symbol: str) -> str:
    """Get Yahoo Finance URL for a stock symbol."""
    return f"{YAHOO_FINANCE_BASE_URL}/quote/{symbol}"

# Scraping Settings
DELAY_SECONDS = 1.0  # Delay between requests
REQUEST_TIMEOUT = 30  # Timeout in seconds

# Storage Settings
DATA_DIR = "data"
STOCKS_JSON = "data/stocks.json"
STOCKS_HISTORY_JSON = "data/stocks_history_10d.json"
MY_STOCKS_JSON = "data/my_stocks.json"
MY_STOCKS_HISTORY_JSON = "data/my_stocks_history_10d.json"
MY_HOLDINGS_JSON = "data/my_holdings.json"
DAILY_PNL_JSON = "data/daily_pnl.json"
BROKER_MOVES_DIR = "data/broker_moves"
HISTORY_DIR = "data/history"

# Scheduling Settings
SCRAPE_TIME = "17:00"  # 5 PM daily scraping

# Gemini API Key (for AI summaries)
# Get your key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = "your-gemini-api-key-here"

# Legacy settings (kept for backward compatibility)
BASE_URL = "https://quotes.toscrape.com/"
TARGET_AUTHOR = "Albert Einstein"

# Database Configuration (kept for future use)
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "your-db-password-here",
    "database": "scraper",
}
