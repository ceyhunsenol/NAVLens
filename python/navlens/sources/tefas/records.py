"""Provider records parsed from TEFAS price-history payloads."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TefasPriceRecord:
    """Represent one dated unit price before Rust domain validation."""

    market_date: date
    fund_code: str
    unit_price: float
