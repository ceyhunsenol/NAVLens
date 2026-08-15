"""Raw Yahoo chart response and retrieval provenance."""

from dataclasses import dataclass
from datetime import datetime

from navlens._timestamps import validate_utc_timestamp

from .errors import YahooSecurityPricePayloadError


@dataclass(frozen=True, slots=True)
class YahooChartHttpResponse:
    """Preserve exact response bytes and the UTC instant they were retrieved."""

    body: bytes
    source_url: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.body, bytes):
            raise YahooSecurityPricePayloadError("response body must be bytes")
        if not isinstance(self.source_url, str) or not self.source_url:
            raise YahooSecurityPricePayloadError("source_url must be a non-empty string")
        validate_utc_timestamp(
            self.retrieved_at,
            "retrieved_at",
            YahooSecurityPricePayloadError,
        )
