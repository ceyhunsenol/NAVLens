"""Provider-neutral records parsed from the CSV transport format."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CsvPriceRecord:
    market_date: date
    unit_price: float
