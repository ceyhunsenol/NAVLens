"""Shared structural contract for parsed provider price records."""

from datetime import date
from typing import Protocol


class PriceRecord(Protocol):
    """Expose the fields required to create a validated Rust observation."""

    market_date: date
    unit_price: float
