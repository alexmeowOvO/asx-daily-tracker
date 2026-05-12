"""
Evening Wrap Scraper - Scrapes daily Evening Wrap articles from Market Index.

Website: https://www.marketindex.com.au/news
Target: Evening Wrap articles published daily
"""

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional, List

from playwright.sync_api import sync_playwright, Page, Browser


@dataclass
class EveningWrapArticle:
    """Data model for an Evening Wrap article."""
    title: str
    url: str
    date: str
    content: str
    images: List[str]  # List of chart/image URLs
    scraped_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class EveningWrapScraper:
    """Scrapes Evening Wrap articles from Market Index."""

    BASE_URL = "https://www.marketindex.com.au"
    NEWS_URL = "https://www.marketindex.com.au/news"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, headless: bool = False):
        """
        Initialize the scraper.

        Args:
            headless: Run browser in headless mode. Set to False to bypass Cloudflare.
        """
        self.headless = headless

    def _wait_for_cloudflare(self, page: Page, timeout: int = 20) -> bool:
        """
        Wait for Cloudflare challenge to complete.

        Args:
            page: Playwright page instance
            timeout: Maximum seconds to wait

        Returns:
            True if challenge passed, False otherwise
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                title = page.title()
                if "moment" not in title.lower() and "cloudflare" not in title.lower():
                    return True
            except Exception:
                pass  # page is mid-navigation, retry
            time.sleep(1)
        return False

    def _fix_mojibake(self, text: str) -> str:
        """
        Repair common UTF-8-as-cp1252 mojibake sequences.

        This fixes artifacts like "â€™" -> "'" and "ðŸ'ª" -> "💪".
        """
        if not text:
            return text

        suspects = ("\xe2\x80\x99", "\xe2\x80\x9c", "\xe2\x80", "\xc2", "\xc3", "\xf0\x9f")
        if not any(s in text for s in suspects):
            return text

        try:
            return text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    def _clean_article_content(self, content: str) -> str:
        """
        Clean article content by removing metadata and keeping only the article body.

        Removes: read time, share buttons, mentioned stocks section, etc.
        Keeps: Content starting from the actual article body after metadata.
        Preserves: [IMAGE:N] markers throughout.
        """
        if not content:
            return content

        # Extract all image markers and their positions relative to text
        image_pattern = r'\[IMAGE:\d+\]'

        # The article has metadata like "MENTIONED\n\n29M\n$792.9M..." followed by "+15 more"
        # The actual article content starts AFTER this section
        # Look for "+N more" pattern which marks end of MENTIONED section
        more_match = re.search(r"\+\d+ more\n+", content)
        if more_match:
            content = content[more_match.end():]

        # Now find the actual article start (but keep image markers before it)
        patterns = [
            r"The S&P/ASX \d+",  # "The S&P/ASX 200 closed..."
            r"The ASX \d+",      # "The ASX 200..."
            r"Australian shares",  # Alternative opening
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Keep any image markers that appear before the article start
                before_content = content[:match.start()]
                image_markers_before = re.findall(image_pattern, before_content)
                content = content[match.start():]
                # Prepend image markers
                if image_markers_before:
                    content = "\n\n".join(image_markers_before) + "\n\n" + content
                break

        # Remove only the author bio and related news at the very end
        # Keep: Interesting Movers, Broker Moves, Scans sections
        # Remove: ABOUT THE AUTHOR and everything after
        author_match = re.search(r"\nABOUT THE AUTHOR\n", content, re.IGNORECASE)
        if author_match:
            content = content[:author_match.start()]

        return content.strip()

    def _is_valid_chart_image(self, img) -> Optional[str]:
        """Check if an image element is a valid chart and return its URL."""
        src = img.get_attribute("src")
        if not src:
            return None
        # Make absolute URL if relative
        if src.startswith("/"):
            src = self.BASE_URL + src
        # Filter out tiny icons
        width = img.get_attribute("width")
        if width and int(width) < 100:
            return None
        # Skip common non-chart images
        skip_patterns = ["avatar", "icon", "logo", "profile", "author"]
        if any(p in src.lower() for p in skip_patterns):
            return None
        return src

    def _extract_content_with_images(self, page: Page) -> tuple[str, List[str]]:
        """
        Extract article content with image placeholders.

        Walks through block-level elements to preserve paragraph structure.
        Images are replaced with [IMAGE:N] markers.

        Returns:
            Tuple of (content with markers, list of image URLs)
        """
        content_elem = page.query_selector(".full-content")
        if not content_elem:
            for selector in [".block-content", "article", "main"]:
                content_elem = page.query_selector(selector)
                if content_elem:
                    break

        if not content_elem:
            return "", []

        images = []

        # Extract block-level elements with their text and images in order
        result = page.evaluate("""
            (elem) => {
                const items = [];
                const blockTags = ['P', 'DIV', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'LI', 'BLOCKQUOTE', 'FIGURE'];

                function processElement(el) {
                    for (const child of el.children) {
                        // Check for images first
                        if (child.nodeName === 'IMG') {
                            const src = child.getAttribute('src');
                            const width = child.getAttribute('width');
                            items.push({ type: 'img', src: src, width: width });
                        }
                        // Check for images inside figures or other containers
                        const imgs = child.querySelectorAll('img');
                        for (const img of imgs) {
                            const src = img.getAttribute('src');
                            const width = img.getAttribute('width');
                            items.push({ type: 'img', src: src, width: width });
                        }

                        // Get text from block elements
                        if (blockTags.includes(child.nodeName)) {
                            const text = child.innerText.trim();
                            if (text) {
                                items.push({ type: 'text', content: text });
                            }
                        } else if (child.children.length > 0) {
                            // Recurse into containers like sections, divs without direct text
                            processElement(child);
                        }
                    }
                }

                processElement(elem);
                return items;
            }
        """, content_elem)

        parts = []
        seen_images = set()

        for item in result:
            if item['type'] == 'text':
                parts.append(item['content'])
            elif item['type'] == 'img':
                src = item.get('src', '')
                width = item.get('width')
                if src and src not in seen_images:
                    # Make absolute URL
                    if src.startswith("/"):
                        src = self.BASE_URL + src
                    try:
                        if width and int(width) < 100:
                            continue
                    except (ValueError, TypeError):
                        pass
                    # Skip non-chart images
                    skip_patterns = ["avatar", "icon", "logo", "profile", "author"]
                    if any(p in src.lower() for p in skip_patterns):
                        continue
                    # Add marker and save image
                    parts.append(f"[IMAGE:{len(images)}]")
                    images.append(src)
                    seen_images.add(src)

        content = "\n\n".join(parts)
        return content, images

    def find_latest_evening_wrap_url(self, page: Page) -> Optional[str]:
        """
        Find the URL of the latest Evening Wrap article from the news page.

        Args:
            page: Playwright page instance

        Returns:
            Full URL of the latest Evening Wrap article, or None if not found
        """
        print("Navigating to news page...")
        page.goto(self.NEWS_URL, wait_until="domcontentloaded", timeout=60000)

        if not self._wait_for_cloudflare(page):
            print("Failed to bypass Cloudflare challenge")
            return None

        time.sleep(3)  # Additional wait for content to load

        # Find all links containing "evening-wrap" in the href
        links = page.query_selector_all('a[href*="evening-wrap"]')

        for link in links:
            href = link.get_attribute("href")
            if href and "evening-wrap" in href:
                # Skip category links
                if "/category/" in href:
                    continue
                # Return the first actual article link
                if href.startswith("/"):
                    return self.BASE_URL + href
                return href

        return None

    def scrape_article(self, page: Page, url: str) -> Optional[EveningWrapArticle]:
        """
        Scrape the content of an Evening Wrap article.

        Args:
            page: Playwright page instance
            url: Full URL of the article

        Returns:
            EveningWrapArticle object, or None if scraping fails
        """
        print(f"Scraping article: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        if not self._wait_for_cloudflare(page, timeout=30):
            print("Failed to bypass Cloudflare challenge")
            return None

        time.sleep(8)  # Wait for dynamic content

        # Extract title
        title_elem = page.query_selector("h1")
        title = title_elem.inner_text().strip() if title_elem else "Unknown Title"
        title = self._fix_mojibake(title)

        # Extract date - look for date patterns in the page
        date = datetime.now().strftime("%Y-%m-%d")  # Default to today
        date_selectors = [
            '[class*="date"]',
            '[class*="published"]',
            '[class*="time"]',
            'time',
        ]
        for selector in date_selectors:
            elem = page.query_selector(selector)
            if elem:
                date_text = elem.inner_text().strip()
                # Try to extract date from text like "Thu 29 Jan 26" or "Fri 06 Feb 26"
                match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{2,4})', date_text)
                if match:
                    day = int(match.group(1))
                    month_str = match.group(2)
                    year_str = match.group(3)
                    # Convert month name to number
                    months = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    month = months.get(month_str.lower()[:3], 1)
                    # Handle 2-digit year
                    year = int(year_str)
                    if year < 100:
                        year += 2000
                    date = f"{year:04d}-{month:02d}-{day:02d}"
                    break

        # Extract content with images in their original positions
        content, images = self._extract_content_with_images(page)
        content = self._fix_mojibake(content)
        content = self._clean_article_content(content)
        print(f"Found {len(images)} chart images")

        if not content:
            print("Warning: Could not extract article content")
            return None

        return EveningWrapArticle(
            title=title,
            url=url,
            date=date,
            content=content,
            images=images,
            scraped_at=datetime.now().isoformat(),
        )

    def scrape_latest(self) -> Optional[EveningWrapArticle]:
        """
        Scrape the latest Evening Wrap article.

        Returns:
            EveningWrapArticle object, or None if scraping fails
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent=self.USER_AGENT)
            page = context.new_page()

            try:
                # Find the latest article URL
                url = self.find_latest_evening_wrap_url(page)
                if not url:
                    print("Could not find Evening Wrap article")
                    return None

                # Scrape the article
                article = self.scrape_article(page, url)
                return article

            finally:
                browser.close()

    def save_article(self, article: EveningWrapArticle, output_dir: str = "data") -> str:
        """
        Save an article to JSON file.

        Args:
            article: The article to save
            output_dir: Directory to save the file

        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)

        # Create filename from article's actual date (not scrape date)
        # article.date is in format YYYY-MM-DD
        date_str = article.date.replace("-", "")
        filename = f"evening_wrap_{date_str}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved article to {filepath}")
        return filepath


def main():
    """Main entry point for scraping Evening Wrap."""
    print("Evening Wrap Scraper")
    print("=" * 60)

    scraper = EveningWrapScraper(headless=False)  # Use visible browser for Cloudflare
    article = scraper.scrape_latest()

    if article:
        print(f"\nTitle: {article.title}")
        print(f"Date: {article.date}")
        print(f"Content length: {len(article.content)} characters")
        print(f"URL: {article.url}")

        # Save the article
        filepath = scraper.save_article(article)
        print(f"\nArticle saved to: {filepath}")
    else:
        print("Failed to scrape Evening Wrap article")


if __name__ == "__main__":
    main()
