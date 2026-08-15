import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from navlens.sources.yahoo import (
    YAHOO_SOURCE_ID,
    YahooAcquisitionPolicy,
    YahooAcquisitionProvenance,
    YahooChartHttpResponse,
    YahooSecurityPriceCacheIntegrityError,
    YahooSecurityPricePayloadError,
    YahooSecurityPriceRateLimitError,
    YahooSecurityPriceRequest,
    YahooSecurityPriceSource,
    YahooSecurityPriceSourceError,
    YahooSymbolMapping,
)


def _sample_payload(symbol: str = "SYNTH.IS") -> bytes:
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
                        "timestamp": [1784514600, 1784601000, 1784687400],
                        "indicators": {"quote": [{"close": [10.0, None, 10.5]}]},
                    }
                ],
            }
        }
    ).encode("utf-8")


class MockClient:
    def __init__(
        self,
        responses: list[YahooChartHttpResponse | Exception],
    ) -> None:
        self._responses = list(responses)
        self.call_count = 0
        self.requests: list[YahooSecurityPriceRequest] = []

    def fetch_chart_response(self, request: YahooSecurityPriceRequest) -> YahooChartHttpResponse:
        self.call_count += 1
        self.requests.append(request)
        if not self._responses:
            raise RuntimeError("no more mock responses")
        outcome = self._responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _sample_request() -> YahooSecurityPriceRequest:
    return YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )


def test_cache_miss_calls_network_and_stores_artifact(tmp_path: Path) -> None:
    request = _sample_request()
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    response = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=retrieved_at,
    )
    client = MockClient([response])
    source = YahooSecurityPriceSource(
        client=client,
        cache_root=tmp_path,
        clock=lambda: retrieved_at,
    )

    result = source.acquire(request)

    assert client.call_count == 1
    assert len(result.snapshots) == 2
    assert result.provenance.is_from_cache is False
    assert result.provenance.is_stale_fallback is False
    assert result.provenance.retrieved_at == retrieved_at
    assert result.provenance.payload_path is not None
    assert result.provenance.payload_path.is_file()

    # Verify snapshots
    assert [s.observation.price.value for s in result.snapshots] == [10.0, 10.5]
    assert all(s.available_at == retrieved_at for s in result.snapshots)
    assert all(s.source_id == YAHOO_SOURCE_ID for s in result.snapshots)


def test_exact_cache_hit_avoids_network_completely(tmp_path: Path) -> None:
    request = _sample_request()
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    response = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=retrieved_at,
    )
    client = MockClient([response])
    policy = YahooAcquisitionPolicy(cache_ttl=timedelta(hours=24))
    source = YahooSecurityPriceSource(
        client=client,
        cache_root=tmp_path,
        policy=policy,
        clock=lambda: retrieved_at,
    )

    # First call primes cache
    res1 = source.acquire(request, checked_at=retrieved_at)
    assert client.call_count == 1
    assert res1.provenance.is_from_cache is False

    # Second call 1 hour later: exact cache hit with 0 additional HTTP calls
    check_time = retrieved_at + timedelta(hours=1)
    res2 = source.acquire(request, checked_at=check_time)
    assert client.call_count == 1  # Network was NOT called!
    assert res2.provenance.is_from_cache is True
    assert res2.provenance.is_stale_fallback is False
    assert res2.provenance.retrieved_at == retrieved_at
    assert [s.observation.price.value for s in res2.snapshots] == [10.0, 10.5]
    assert all(s.available_at == retrieved_at for s in res2.snapshots)


def test_429_without_cache_raises_typed_rate_limit_error(tmp_path: Path) -> None:
    request = _sample_request()
    error = YahooSecurityPriceRateLimitError("rate limited", retry_after="60")
    client = MockClient([error])
    source = YahooSecurityPriceSource(client=client, cache_root=tmp_path)

    with pytest.raises(YahooSecurityPriceRateLimitError) as exc_info:
        source.acquire(request)

    assert exc_info.value.retry_after == "60"
    assert exc_info.value.retry_after_seconds == 60
    assert client.call_count == 1


def test_429_with_allowed_stale_cache_returns_marked_fallback(tmp_path: Path) -> None:
    request = _sample_request()
    initial_retrieval = datetime(2026, 7, 20, 12, tzinfo=UTC)
    response = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=initial_retrieval,
    )
    # First call succeeds, second call returns 429
    rate_error = YahooSecurityPriceRateLimitError("rate limit", retry_after="30")
    client = MockClient([response, rate_error])
    policy = YahooAcquisitionPolicy(
        cache_ttl=timedelta(hours=24),
        allow_stale_on_429=True,
    )
    source = YahooSecurityPriceSource(
        client=client,
        cache_root=tmp_path,
        policy=policy,
    )

    # Prime cache on July 20
    source.acquire(request, checked_at=initial_retrieval)
    assert client.call_count == 1

    # July 23: Cache is stale (>24h). Network is called and returns 429.
    # Stale fallback policy allows returning valid cached data with explicit provenance.
    current_time = datetime(2026, 7, 23, 15, tzinfo=UTC)
    result = source.acquire(request, checked_at=current_time)

    assert client.call_count == 2
    assert result.provenance.is_from_cache is True
    assert result.provenance.is_stale_fallback is True
    assert result.provenance.retrieved_at == initial_retrieval
    assert [s.observation.price.value for s in result.snapshots] == [10.0, 10.5]
    # Invariant: Snapshot available_at retains real historical retrieval time, NOT current time!
    assert all(s.available_at == initial_retrieval for s in result.snapshots)


def test_429_with_fallback_disabled_raises_error_even_with_stale_cache(tmp_path: Path) -> None:
    request = _sample_request()
    initial_retrieval = datetime(2026, 7, 20, 12, tzinfo=UTC)
    response = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=initial_retrieval,
    )
    rate_error = YahooSecurityPriceRateLimitError("rate limit", retry_after="30")
    client = MockClient([response, rate_error])
    policy = YahooAcquisitionPolicy(
        cache_ttl=timedelta(hours=24),
        allow_stale_on_429=False,  # Fallback disabled!
    )
    source = YahooSecurityPriceSource(
        client=client,
        cache_root=tmp_path,
        policy=policy,
    )

    # Prime cache
    source.acquire(request, checked_at=initial_retrieval)

    # Try fetching when stale -> 429 must be raised
    current_time = datetime(2026, 7, 23, 15, tzinfo=UTC)
    with pytest.raises(YahooSecurityPriceRateLimitError) as exc_info:
        source.acquire(request, checked_at=current_time)

    assert exc_info.value.retry_after == "30"


def test_force_refresh_bypasses_cache_and_calls_network(tmp_path: Path) -> None:
    request = _sample_request()
    t1 = datetime(2026, 7, 20, 12, tzinfo=UTC)
    t2 = datetime(2026, 7, 20, 13, tzinfo=UTC)
    resp1 = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=t1,
    )
    resp2 = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=t2,
    )
    client = MockClient([resp1, resp2])
    policy = YahooAcquisitionPolicy(cache_ttl=timedelta(hours=24), force_refresh=True)
    source = YahooSecurityPriceSource(client=client, cache_root=tmp_path, policy=policy)

    res1 = source.acquire(request, checked_at=t1)
    assert client.call_count == 1
    assert res1.provenance.is_from_cache is False

    res2 = source.acquire(request, checked_at=t1 + timedelta(minutes=5))
    assert client.call_count == 2
    assert res2.provenance.is_from_cache is False
    assert res2.provenance.retrieved_at == t2


def test_rejects_clock_anomaly_in_acquirer(tmp_path: Path) -> None:
    request = _sample_request()
    t1 = datetime(2026, 7, 23, 12, tzinfo=UTC)
    resp = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=t1,
    )
    client = MockClient([resp])
    source = YahooSecurityPriceSource(client=client, cache_root=tmp_path)
    source.acquire(request, checked_at=t1)

    # If clock goes backwards, it must raise integrity error
    past_time = t1 - timedelta(hours=1)
    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="clock anomaly"):
        source.acquire(request, checked_at=past_time)


def test_backward_compatible_fetch_delegates_to_acquire(tmp_path: Path) -> None:
    request = _sample_request()
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    resp = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=retrieved_at,
    )
    client = MockClient([resp])
    source = YahooSecurityPriceSource(client=client, cache_root=tmp_path)

    snapshots = source.fetch(request)

    assert isinstance(snapshots, tuple)
    assert len(snapshots) == 2
    assert [s.observation.price.value for s in snapshots] == [10.0, 10.5]


def test_malformed_network_payload_does_not_poison_cache(tmp_path: Path) -> None:
    request = _sample_request()
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    malformed_resp = YahooChartHttpResponse(
        body=b'{"chart": {"error": {"code": "Malformed"}}}',
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=retrieved_at,
    )
    client = MockClient([malformed_resp])
    source = YahooSecurityPriceSource(client=client, cache_root=tmp_path)

    with pytest.raises(YahooSecurityPricePayloadError):
        source.acquire(request)

    # Prove no files were written to cache root
    assert list(tmp_path.iterdir()) == []


def test_429_fallback_with_fresh_cache_marks_rate_limit_fallback_without_stale(
    tmp_path: Path,
) -> None:
    request = _sample_request()
    t0 = datetime(2026, 7, 20, 12, tzinfo=UTC)
    response = YahooChartHttpResponse(
        body=_sample_payload(),
        source_url="https://example.invalid/chart/SYNTH.IS",
        retrieved_at=t0,
    )
    rate_error = YahooSecurityPriceRateLimitError("rate limit", retry_after="30")
    client = MockClient([response, rate_error])
    policy = YahooAcquisitionPolicy(
        cache_ttl=timedelta(hours=24),
        force_refresh=True,  # Force refresh tries network even though cache is fresh
        allow_stale_on_429=True,
    )
    source = YahooSecurityPriceSource(
        client=client,
        cache_root=tmp_path,
        policy=policy,
    )

    # Prime cache
    source.acquire(request, checked_at=t0)

    # 10 minutes later: force_refresh triggers network, which returns 429.
    # Cache is fresh (age 10 min < 24h). Fallback occurs, but is_stale is False!
    t1 = t0 + timedelta(minutes=10)
    result = source.acquire(request, checked_at=t1)

    assert result.provenance.is_from_cache is True
    assert result.provenance.is_rate_limit_fallback is True
    assert result.provenance.is_stale is False
    assert result.provenance.is_stale_fallback is False
    assert result.provenance.retrieved_at == t0


def test_provenance_rejects_contradictory_flags() -> None:
    t0 = datetime(2026, 7, 20, 12, tzinfo=UTC)
    sha = "a" * 64

    # Rate-limit fallback without is_from_cache=True
    with pytest.raises(YahooSecurityPriceSourceError, match="rate-limit fallback requires"):
        YahooAcquisitionProvenance(
            source_url="https://example.invalid",
            retrieved_at=t0,
            sha256_hex=sha,
            is_from_cache=False,
            is_rate_limit_fallback=True,
            is_stale=False,
        )

    # Network response marked stale
    with pytest.raises(YahooSecurityPriceSourceError, match="cannot be marked stale"):
        YahooAcquisitionProvenance(
            source_url="https://example.invalid",
            retrieved_at=t0,
            sha256_hex=sha,
            is_from_cache=False,
            is_rate_limit_fallback=False,
            is_stale=True,
        )

    # Regular cache hit marked stale
    with pytest.raises(YahooSecurityPriceSourceError, match="cannot be marked stale"):
        YahooAcquisitionProvenance(
            source_url="https://example.invalid",
            retrieved_at=t0,
            sha256_hex=sha,
            is_from_cache=True,
            is_rate_limit_fallback=False,
            is_stale=True,
        )
