"""Explicit input for one TEFAS historical-price request."""

from dataclasses import dataclass
from datetime import date

from .errors import TefasRequestError


@dataclass(frozen=True, slots=True)
class TefasPriceRequest:
    """Identify one fund and inclusive market-date interval to retrieve."""

    fund_code: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not self.fund_code.strip():
            raise TefasRequestError("fund code is required")
        if self.start_date > self.end_date:
            raise TefasRequestError("start date must not be after end date")

    @property
    def normalized_fund_code(self) -> str:
        """Return the provider-facing identifier without owning domain validation."""
        return self.fund_code.strip().upper()
