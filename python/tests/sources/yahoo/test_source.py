import json
from datetime import UTC, date, datetime

import pytest
from navlens.sources.yahoo import (
    YAHOO_SOURCE_ID,
    YahooChartHttpResponse,
    YahooSecurityPricePayloadError,
    YahooSecurityPriceRequest,
    YahooSecurityPriceSource,
    YahooSymbolMapping,
)


def _response(symbol: str = "SYNTH.IS") -> YahooChartHttpResponse:
    body = json.dumps(
        {
            "chart": {
                "error": None,
                "result": [
                    {
                        "meta": {
                            "symbol": symbol,
                            "currency": "TRY",
                            "exchangeTimezoneName": "Europe/Istanbul",
                        },
                        "timestamp": [1784514600, 1784601000, 1784687400],
                        "indicators": {"quote": [{"close": [10.0, None, 10.5]}]},
                    }
                ],
            }
        }
    ).encode()
    return YahooChartHttpResponse(
        body=body,
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=datetime(2026, 7, 23, 12, tzinfo=UTC),
    )


class FakeClient:
    def __init__(self, response: YahooChartHttpResponse) -> None:
        self.response = response
        self.requests: list[YahooSecurityPriceRequest] = []

    def fetch_chart_response(self, request: YahooSecurityPriceRequest) -> YahooChartHttpResponse:
        self.requests.append(request)
        return self.response


def _request() -> YahooSecurityPriceRequest:
    return YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )


def test_maps_unadjusted_closes_with_retrieval_time_provenance() -> None:
    request = _request()
    client = FakeClient(_response())

    snapshots = YahooSecurityPriceSource(client).fetch(request)

    assert client.requests == [request]
    assert [str(snapshot.observation.market_date) for snapshot in snapshots] == [
        "2026-07-20",
        "2026-07-22",
    ]
    assert [snapshot.observation.price.value for snapshot in snapshots] == [10.0, 10.5]
    assert all(snapshot.observation.instrument_id == "SYNTH" for snapshot in snapshots)
    assert all(str(snapshot.observation.currency) == "TRY" for snapshot in snapshots)
    assert all(str(snapshot.observation.adjustment) == "unadjusted" for snapshot in snapshots)
    assert all(snapshot.source_id == YAHOO_SOURCE_ID for snapshot in snapshots)
    assert all(snapshot.available_at == client.response.retrieved_at for snapshot in snapshots)
    assert all(snapshot.ingested_at == client.response.retrieved_at for snapshot in snapshots)


def test_rejects_response_for_a_different_provider_symbol() -> None:
    source = YahooSecurityPriceSource(FakeClient(_response("OTHER.IS")))

    with pytest.raises(YahooSecurityPricePayloadError, match="does not match"):
        source.fetch(_request())
