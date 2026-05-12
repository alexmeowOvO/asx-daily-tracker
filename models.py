from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Stock:
    """Represents a stock listing."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    timestamp: str  # ISO format datetime string
    source_url: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "timestamp": self.timestamp,
            "source_url": self.source_url,
        }

    @staticmethod
    def from_dict(data: dict) -> "Stock":
        """Create Stock from dictionary."""
        return Stock(
            symbol=data["symbol"],
            name=data["name"],
            price=data["price"],
            change=data["change"],
            change_percent=data["change_percent"],
            timestamp=data["timestamp"],
            source_url=data["source_url"],
        )


# Legacy Quote model - kept for backward compatibility
@dataclass(frozen=True)
class Quote:
    author: str
    text: str
    source_url: str

    def as_row(self) -> dict[str, str]:
        return {
            "author": self.author,
            "text": self.text,
            "source_url": self.source_url,
        }
