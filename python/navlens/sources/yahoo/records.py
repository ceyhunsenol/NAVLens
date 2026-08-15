"""Provider-specific records parsed from a Yahoo chart response."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YahooDailyClose:
    """One non-null daily close paired with its provider timestamp."""

    timestamp: int
    close: float


@dataclass(frozen=True, slots=True)
class YahooChartDocument:
    """Validated Yahoo metadata and daily closes before canonical mapping."""

    provider_symbol: str
    currency: str
    exchange_timezone_name: str
    closes: tuple[YahooDailyClose, ...]
