"""
Evening Wrap Summarizer - Uses Google Gemini to generate article summaries.

Reads the evening wrap article and generates a concise summary.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime

from google import genai
from google.genai import types


def load_article(date: str = None) -> dict | None:
    """
    Load an evening wrap article.

    Args:
        date: Date in YYYYMMDD format. If None, loads the latest article.

    Returns:
        Article dictionary or None if not found.
    """
    data_dir = Path("data")

    if date:
        filepath = data_dir / f"evening_wrap_{date}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # Find latest article
    files = sorted(data_dir.glob("evening_wrap_*.json"), reverse=True)
    if not files:
        return None

    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def generate_summary(article: dict, api_key: str, my_stocks: list[str] = None) -> str:
    """
    Generate a summary of the evening wrap article using Gemini.

    Args:
        article: Article dictionary with title and content.
        api_key: Google Gemini API key.
        my_stocks: List of user's stock symbols to watch for.

    Returns:
        Generated summary string.
    """
    client = genai.Client(api_key=api_key)

    # Build the my stocks section if provided
    my_stocks_instruction = ""
    if my_stocks:
        # Convert symbols like "ZIP.AX" to just "ZIP" for matching
        stock_names = [s.replace(".AX", "") for s in my_stocks]
        my_stocks_instruction = f"""
IMPORTANT: The user owns these stocks: {', '.join(stock_names)}
If ANY of these stocks are ACTUALLY MENTIONED in the article, include a "🎯 My Portfolio" section with ONLY the stocks that are mentioned. Do NOT include stocks that are not mentioned in the article. Skip the "My Portfolio" section entirely if none of the user's stocks appear in the article.
"""

    prompt = f"""You are a financial news summarizer. Summarize the following Australian stock market Evening Wrap article in 3-5 bullet points, followed by stock recommendations.

Focus on:
- Overall market performance (ASX 200 movement)
- Key sectors that moved (up or down)
- Notable individual stocks mentioned
- Any significant news or events affecting the market
{my_stocks_instruction}
After the summary, add a "Stocks to Watch" section with:
- 2-3 stocks mentioned positively (potential buys or ones showing strength)
- 2-3 stocks mentioned negatively (potential sells or ones showing weakness)
- Brief reasoning for each (1 sentence)

Keep each bullet point concise (1-2 sentences max).
Use Australian dollar formatting where applicable.
Use stock symbols in ASX format (e.g., CBA, BHP, CSL).

Article Title: {article['title']}

Article Content:
{article['content']}

Format your response as:
• [Summary bullet points]

🎯 My Portfolio (ONLY include this section if user's stocks are mentioned - omit entirely otherwise):
• [SYMBOL] - [What the article says]

📈 Stocks to Watch (Bullish):
• [SYMBOL] - [Brief reason]

📉 Stocks to Watch (Bearish):
• [SYMBOL] - [Brief reason]"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )
    return response.text


def format_content(article: dict, api_key: str) -> str:
    """
    Format the article content using Gemini to clean up tables and structure.

    Args:
        article: Article dictionary with content.
        api_key: Google Gemini API key.

    Returns:
        Formatted content as clean HTML.
    """
    client = genai.Client(api_key=api_key)

    prompt = f"""You are a content formatter. Convert the following financial article content into clean, well-structured HTML.

IMPORTANT RULES:
1. Convert any tabular data (stock prices, indices, broker moves, etc.) into proper HTML tables with <table>, <thead>, <tbody>, <tr>, <th>, <td> tags
2. Use appropriate heading levels for structure:
   - Use <h2> for major sections (like "Markets", "Broker Moves", "Sector Performance")
   - Use <h3> for sub-sections (like "Today's best blue chip gainers", "52-week highs", "Top fallers")
   - Use <h4> for minor headers within sections
3. Use <p> for paragraphs
4. Keep all the original data and numbers exactly as they are
5. For tables, detect column headers and use <th> in <thead>
6. Add appropriate CSS classes: "data-table" for tables, "section-header" for headers
7. Do NOT include <html>, <head>, <body> tags - just the content
8. Do NOT add any commentary or explanations - just output the formatted HTML
9. Preserve all stock symbols, prices, percentages exactly as shown
10. REMOVE any "View all..." link text (like "View all top gainers", "View all 52 week highs", "View all top fallers", etc.) - these are navigation links that don't work without the original website
11. REMOVE any ">REGISTER NOW!<" or similar call-to-action text
12. REMOVE any "More News" link text
13. REMOVE any promotional/webinar sections entirely (like "ChartWatch *LIVE* Webinar", "Places are limited so", webinar registration info, etc.)
14. REMOVE any "Latest News" sections with article links that are not part of the main content
15. REMOVE any author promotional content or newsletter signup sections
16. Focus ONLY on the actual market data, stock tables, analysis, and news content

Article Content:
{article['content']}

Output the formatted HTML only:"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )
    return response.text


def extract_broker_moves(article: dict) -> list[dict]:
    """
    Extract broker moves from the article content.

    Args:
        article: Article dictionary with content.

    Returns:
        List of broker move dictionaries.
    """
    content = article.get("content", "")

    # Find the Broker Moves section
    broker_start = content.find("Broker Moves")
    if broker_start == -1:
        return []

    # Find the end of the section (next major section or end)
    # Common section headers that come after Broker Moves
    end_markers = ["Upcoming Dividends", "Economic News", "Upcoming Events", "ChartWatch", "Latest News"]
    broker_end = len(content)
    for marker in end_markers:
        idx = content.find(marker, broker_start + 12)
        if idx != -1 and idx < broker_end:
            broker_end = idx

    broker_section = content[broker_start:broker_end]

    # Parse individual stocks and their broker recommendations
    moves = []
    lines = broker_section.split("\n")

    current_stock = None
    current_symbol = None

    # Pattern for stock header: "Company Name (SYMBOL)"
    stock_pattern = re.compile(r"^([A-Za-z0-9\s\.\-&']+)\s*\(([A-Z0-9]+)\)\s*$")

    # Pattern for broker recommendation
    # e.g., "Retained at outperform at CLSA; Price Target: $80.00"
    # e.g., "Downgraded to accumulate from buy at Ord Minnett; Price Target: $70.00 from $73.00"
    # e.g., "Initiated at buy at Shaw and Partners; Price Target: $0.23"
    broker_pattern = re.compile(
        r"^(Retained|Upgraded|Downgraded|Initiated)\s+"
        r"(?:at|to)\s+(\w+(?:\s+\w+)?)\s*"  # rating (e.g., "outperform", "speculative buy")
        r"(?:from\s+(\w+(?:\s+\w+)?)\s*)?"  # previous rating (optional)
        r"at\s+([A-Za-z\s&]+?);\s*"  # broker name
        r"Price Target:\s*\$?([\d,\.]+)"  # price target
        r"(?:\s+from\s+\$?([\d,\.]+))?"  # previous price target (optional)
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if it's a stock header
        stock_match = stock_pattern.match(line)
        if stock_match:
            current_stock = stock_match.group(1).strip()
            current_symbol = stock_match.group(2).strip()
            continue

        # Check if it's a broker recommendation
        if current_stock and current_symbol:
            broker_match = broker_pattern.match(line)
            if broker_match:
                action = broker_match.group(1)
                rating = broker_match.group(2).lower()
                prev_rating = broker_match.group(3)
                broker = broker_match.group(4).strip()
                price_target = float(broker_match.group(5).replace(",", ""))
                prev_price_target = broker_match.group(6)

                move = {
                    "symbol": current_symbol,
                    "name": current_stock,
                    "broker": broker,
                    "action": action.lower(),
                    "rating": rating,
                    "price_target": price_target,
                }

                if prev_rating:
                    move["previous_rating"] = prev_rating.lower()
                if prev_price_target:
                    move["previous_price_target"] = float(prev_price_target.replace(",", ""))

                moves.append(move)

    return moves


def save_broker_moves(date: str, moves: list[dict]):
    """
    Save broker moves to a separate JSON file.

    Args:
        date: Date in YYYYMMDD format or YYYY-MM-DD.
        moves: List of broker move dictionaries.
    """
    from config import BROKER_MOVES_DIR

    broker_dir = Path(BROKER_MOVES_DIR)
    broker_dir.mkdir(parents=True, exist_ok=True)

    # Normalize date format
    date_normalized = date.replace("-", "")

    filepath = broker_dir / f"broker_moves_{date_normalized}.json"

    data = {
        "date": date,
        "extracted_at": datetime.now().isoformat(),
        "count": len(moves),
        "moves": moves,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Broker moves saved to {filepath} ({len(moves)} entries)")


def save_summary(date: str, summary: str, formatted_content: str = None):
    """
    Save summary and formatted content to the article JSON file.

    Args:
        date: Date in YYYYMMDD format.
        summary: Generated summary text.
        formatted_content: HTML-formatted article content.
    """
    filepath = Path("data") / f"evening_wrap_{date}.json"

    if not filepath.exists():
        print(f"Article file not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        article = json.load(f)

    article["summary"] = summary
    article["summary_generated_at"] = datetime.now().isoformat()

    if formatted_content:
        article["formatted_content"] = formatted_content
        article["content_formatted_at"] = datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)

    print(f"[OK] Summary saved to {filepath}")


def main():
    """Main entry point."""
    print("Evening Wrap Summarizer")
    print("=" * 60)

    # Get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("\nTo set it:")
        print("  Windows: set GEMINI_API_KEY=your_api_key_here")
        print("  Linux/Mac: export GEMINI_API_KEY=your_api_key_here")
        return

    # Load user's stocks from config
    try:
        from config import MY_STOCKS
        print(f"Watching for your stocks: {', '.join(MY_STOCKS)}")
    except ImportError:
        MY_STOCKS = []

    # Load latest article
    article = load_article()

    if not article:
        print("No evening wrap articles found")
        return

    print(f"Article: {article['title']}")
    print(f"Date: {article['date']}")
    print(f"Content length: {len(article['content'])} characters")

    # Check if summary already exists - always regenerate when running non-interactively
    if article.get("summary"):
        print("\nSummary already exists, regenerating...")

    print("\nGenerating summary with Gemini...")

    try:
        summary = generate_summary(article, api_key, MY_STOCKS)
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print(summary)

        # Always regenerate formatted content along with summary
        print("\nFormatting article content...")
        formatted_content = format_content(article, api_key)
        print("[OK] Content formatted")

        # Extract date from filename
        date = datetime.now().strftime("%Y%m%d")
        # Try to get date from article
        if "scraped_at" in article:
            date = article["scraped_at"][:10].replace("-", "")

        # Find actual file date
        data_dir = Path("data")
        files = sorted(data_dir.glob("evening_wrap_*.json"), reverse=True)
        if files:
            date = files[0].stem.replace("evening_wrap_", "")

        save_summary(date, summary, formatted_content)

        # Extract and save broker moves
        print("\nExtracting broker moves...")
        broker_moves = extract_broker_moves(article)
        if broker_moves:
            save_broker_moves(article.get("date", date), broker_moves)
        else:
            print("[!] No broker moves found in article")

    except Exception as e:
        print(f"Error generating summary: {e}")


if __name__ == "__main__":
    main()
