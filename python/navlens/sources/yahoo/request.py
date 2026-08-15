"""Explicit request contract for Yahoo daily security prices."""

from dataclasses import dataclass
from datetime import date

from .errors import YahooSecurityPriceRequestError
from .symbol_mapping import YahooSymbolMapping


@dataclass(frozen=True, slots=True)
class YahooSecurityPriceRequest:
    """Request one mapped instrument over an inclusive market-date interval."""

    mapping: YahooSymbolMapping
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, YahooSymbolMapping):
            raise YahooSecurityPriceRequestError("mapping must be a YahooSymbolMapping")
        if type(self.start_date) is not date or type(self.end_date) is not date:
            raise YahooSecurityPriceRequestError("start_date and end_date must be dates")
        if self.start_date > self.end_date:
            raise YahooSecurityPriceRequestError("start_date must not be after end_date")
