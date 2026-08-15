"""Orchestration for experimental Yahoo security-price acquisition."""

from typing import Protocol

from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot

from .client import YahooChartHttpClient
from .parser import parse_yahoo_chart_response
from .request import YahooSecurityPriceRequest
from .response import YahooChartHttpResponse
from .snapshots import materialize_yahoo_security_price_snapshots


class YahooChartResponseClient(Protocol):
    """Consumer-owned transport capability required by the Yahoo source."""

    def fetch_chart_response(
        self, request: YahooSecurityPriceRequest
    ) -> YahooChartHttpResponse: ...


class YahooSecurityPriceSource:
    """Acquire unadjusted daily closes from Yahoo's experimental chart boundary."""

    def __init__(self, client: YahooChartResponseClient | None = None) -> None:
        self._client = client or YahooChartHttpClient()

    def fetch(
        self,
        request: YahooSecurityPriceRequest,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        """Fetch and map one instrument without fabricating historical publication times."""
        response = self._client.fetch_chart_response(request)
        document = parse_yahoo_chart_response(response.body)
        return materialize_yahoo_security_price_snapshots(
            document,
            request.mapping,
            response.retrieved_at,
        )
