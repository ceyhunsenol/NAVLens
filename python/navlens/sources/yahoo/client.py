"""HTTP transport for Yahoo Finance's experimental chart endpoint."""

import math
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .errors import YahooSecurityPriceRateLimitError, YahooSecurityPriceTransportError
from .request import YahooSecurityPriceRequest
from .response import YahooChartHttpResponse

_CHART_ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _epoch_seconds(value: datetime) -> int:
    return int(value.timestamp())


def _build_chart_url(request: YahooSecurityPriceRequest) -> str:
    start = datetime.combine(request.start_date, time.min, UTC)
    end_exclusive = datetime.combine(request.end_date + timedelta(days=1), time.min, UTC)
    query = urlencode(
        {
            "period1": _epoch_seconds(start),
            "period2": _epoch_seconds(end_exclusive),
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
    )
    symbol = quote(request.mapping.normalized_provider_symbol, safe=".-")
    return f"{_CHART_ENDPOINT}/{symbol}?{query}"


def _extract_retry_after(error: HTTPError) -> str | None:
    if error.headers is None:
        return None
    raw = error.headers.get("Retry-After")
    if raw is None or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped if stripped else None


class YahooChartHttpClient:
    """Fetch chart payloads without parsing or normalizing financial fields."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a finite positive number")
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def fetch_chart_response(self, request: YahooSecurityPriceRequest) -> YahooChartHttpResponse:
        """Fetch one chart response without retries or access-control workarounds."""
        url = _build_chart_url(request)
        http_request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "NAVLens/0.1 (+https://github.com/ceyhunsenol/NAVLens)",
            },
            method="GET",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                body = response.read()
        except HTTPError as error:
            if error.code == 429:
                retry_after = _extract_retry_after(error)
                raise YahooSecurityPriceRateLimitError(
                    "Yahoo chart rate limit reached",
                    retry_after=retry_after,
                ) from error
            raise YahooSecurityPriceTransportError(
                f"Yahoo chart request returned HTTP {error.code}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise YahooSecurityPriceTransportError("Yahoo chart request failed") from error
        return YahooChartHttpResponse(body=body, source_url=url, retrieved_at=self._clock())
