"""Exact canonical-to-provider symbol mapping for Yahoo Finance."""

from dataclasses import dataclass

from .errors import YahooSecurityPriceRequestError


@dataclass(frozen=True, slots=True)
class YahooSymbolMapping:
    """Map one NAVLens instrument identifier to one exact Yahoo symbol."""

    instrument_id: str
    provider_symbol: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, str) or not self.instrument_id.strip():
            raise YahooSecurityPriceRequestError("instrument_id must be a non-empty string")
        if not isinstance(self.provider_symbol, str) or not self.provider_symbol.strip():
            raise YahooSecurityPriceRequestError("provider_symbol must be a non-empty string")

    @property
    def normalized_instrument_id(self) -> str:
        """Return the exact canonical identifier without surrounding whitespace."""
        return self.instrument_id.strip()

    @property
    def normalized_provider_symbol(self) -> str:
        """Return Yahoo's symbol in its canonical uppercase spelling."""
        return self.provider_symbol.strip().upper()
