"""Tests for YahooSecurityPriceSourceAdapter."""

import json
from datetime import UTC, date, datetime
from types import MappingProxyType

import pytest
from navlens.datasets import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)
from navlens.sources.yahoo import (
    YAHOO_SOURCE_ID,
    YahooChartHttpResponse,
    YahooSecurityPriceCacheError,
    YahooSecurityPriceCacheIntegrityError,
    YahooSecurityPricePayloadError,
    YahooSecurityPriceRateLimitError,
    YahooSecurityPriceRequest,
    YahooSecurityPriceRequestError,
    YahooSecurityPriceSource,
    YahooSecurityPriceSourceAdapter,
    YahooSecurityPriceTransportError,
    YahooSymbolMapping,
)


def _sample_payload(symbol: str = "GARAN.IS") -> bytes:
    return json.dumps(
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
                        "timestamp": [1784514600, 1784601000],
                        "indicators": {"quote": [{"close": [10.0, 10.5]}]},
                    }
                ],
            }
        }
    ).encode("utf-8")


class MockClient:
    def __init__(self, responses: list[YahooChartHttpResponse | Exception]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    def fetch_chart_response(self, request: YahooSecurityPriceRequest) -> YahooChartHttpResponse:
        self.call_count += 1
        if not self._responses:
            raise RuntimeError("no more mock responses")
        outcome = self._responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_adapter_constructor_validates_mappings_and_duplicates() -> None:
    client = MockClient([])
    source = YahooSecurityPriceSource(client=client)

    # Valid mapping construction
    m1 = YahooSymbolMapping("TRY_GARAN", "GARAN.IS")
    m2 = YahooSymbolMapping("TRY_AKBNK", "AKBNK.IS")
    adapter = YahooSecurityPriceSourceAdapter(source, [m1, m2])
    assert adapter.source_id == YAHOO_SOURCE_ID
    assert isinstance(adapter.mappings, MappingProxyType)
    assert len(adapter.mappings) == 2

    # Reject duplicate normalized canonical ID
    m1_dup = YahooSymbolMapping("  TRY_GARAN  ", "GARAN2.IS")
    with pytest.raises(ValueError, match="duplicate mapping"):
        YahooSecurityPriceSourceAdapter(source, [m1, m1_dup])

    # Reject invalid item type
    with pytest.raises(TypeError, match="YahooSymbolMapping"):
        YahooSecurityPriceSourceAdapter(source, [m1, "not_a_mapping"])  # type: ignore[list-item]

    # Reject invalid source type
    with pytest.raises(TypeError, match="YahooSecurityPriceSource"):
        YahooSecurityPriceSourceAdapter("not_a_source", [m1])  # type: ignore[arg-type]


def test_adapter_successful_fetch() -> None:
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    resp = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/GARAN.IS",
        retrieved_at=retrieved_at,
    )
    client = MockClient([resp])
    source = YahooSecurityPriceSource(client=client)
    mapping = YahooSymbolMapping("TRY_GARAN", "GARAN.IS")
    adapter = YahooSecurityPriceSourceAdapter(source, [mapping])

    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 21))
    snapshots = adapter.fetch_security_prices(query)

    assert len(snapshots) == 2
    assert [s.observation.price.value for s in snapshots] == [10.0, 10.5]
    assert all(s.source_id == YAHOO_SOURCE_ID for s in snapshots)


def test_adapter_unmapped_instrument_raises_error() -> None:
    client = MockClient([])
    source = YahooSecurityPriceSource(client=client)
    mapping = YahooSymbolMapping("TRY_GARAN", "GARAN.IS")
    adapter = YahooSecurityPriceSourceAdapter(source, [mapping])

    query = SecurityPriceQuery("TRY_UNMAPPED", date(2026, 7, 20), date(2026, 7, 21))
    with pytest.raises(SecurityPriceUnmappedInstrumentError, match="TRY_UNMAPPED"):
        adapter.fetch_security_prices(query)


def test_adapter_rejects_non_query_type() -> None:
    client = MockClient([])
    source = YahooSecurityPriceSource(client=client)
    adapter = YahooSecurityPriceSourceAdapter(source, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")])

    with pytest.raises(TypeError, match="SecurityPriceQuery"):
        adapter.fetch_security_prices("TRY_GARAN")  # type: ignore[arg-type]


def test_adapter_maps_transport_and_cache_errors_to_unavailable() -> None:
    # Rate limit error -> Unavailable
    client = MockClient([YahooSecurityPriceRateLimitError("rate limited", retry_after="30")])
    source = YahooSecurityPriceSource(client=client)
    adapter = YahooSecurityPriceSourceAdapter(source, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")])
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 21))

    with pytest.raises(SecurityPriceSourceUnavailableError) as exc_info:
        adapter.fetch_security_prices(query)
    assert isinstance(exc_info.value.__cause__, YahooSecurityPriceTransportError)

    # Generic transport error -> Unavailable
    client2 = MockClient([YahooSecurityPriceTransportError("network down")])
    source2 = YahooSecurityPriceSource(client=client2)
    adapter2 = YahooSecurityPriceSourceAdapter(
        source2, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")]
    )
    with pytest.raises(SecurityPriceSourceUnavailableError) as exc_info2:
        adapter2.fetch_security_prices(query)
    assert isinstance(exc_info2.value.__cause__, YahooSecurityPriceTransportError)

    # Generic cache error -> Unavailable
    client3 = MockClient([YahooSecurityPriceCacheError("disk full")])
    source3 = YahooSecurityPriceSource(client=client3)
    adapter3 = YahooSecurityPriceSourceAdapter(
        source3, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")]
    )
    with pytest.raises(SecurityPriceSourceUnavailableError) as exc_info3:
        adapter3.fetch_security_prices(query)
    assert isinstance(exc_info3.value.__cause__, YahooSecurityPriceCacheError)


def test_adapter_maps_payload_and_integrity_errors_to_corrupted() -> None:
    # Payload error -> Corrupted
    client = MockClient([YahooSecurityPricePayloadError("invalid schema")])
    source = YahooSecurityPriceSource(client=client)
    adapter = YahooSecurityPriceSourceAdapter(source, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")])
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 21))

    with pytest.raises(SecurityPriceCorruptedSourceDataError) as exc_info:
        adapter.fetch_security_prices(query)
    assert isinstance(exc_info.value.__cause__, YahooSecurityPricePayloadError)

    # Integrity error -> Corrupted (caught before general CacheError)
    client2 = MockClient([YahooSecurityPriceCacheIntegrityError("digest mismatch")])
    source2 = YahooSecurityPriceSource(client=client2)
    adapter2 = YahooSecurityPriceSourceAdapter(
        source2, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")]
    )
    with pytest.raises(SecurityPriceCorruptedSourceDataError) as exc_info2:
        adapter2.fetch_security_prices(query)
    assert isinstance(exc_info2.value.__cause__, YahooSecurityPriceCacheIntegrityError)


def test_adapter_propagates_unexpected_contract_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MockClient([])
    source = YahooSecurityPriceSource(client=client)
    adapter = YahooSecurityPriceSourceAdapter(source, [YahooSymbolMapping("TRY_GARAN", "GARAN.IS")])
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 21))

    def failing_fetch(req: YahooSecurityPriceRequest):
        raise YahooSecurityPriceRequestError("programming contract violated")

    monkeypatch.setattr(source, "fetch", failing_fetch)
    with pytest.raises(YahooSecurityPriceRequestError):
        adapter.fetch_security_prices(query)
