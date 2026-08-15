from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from navlens.sources.yahoo import (
    YahooAcquisitionProvenance,
    YahooSecurityPriceAcquisitionResult,
    YahooSecurityPriceBatchError,
    YahooSecurityPriceBatchFailure,
    YahooSecurityPriceBatchSuccess,
    YahooSecurityPriceRateLimitError,
    YahooSecurityPriceRequest,
    YahooSecurityPriceSourceError,
    YahooSymbolMapping,
    acquire_yahoo_security_price_batch,
)

_CHECKED_AT = datetime(2026, 8, 15, 9, tzinfo=UTC)


def _request(instrument_id: str, symbol: str) -> YahooSecurityPriceRequest:
    return YahooSecurityPriceRequest(
        YahooSymbolMapping(instrument_id, symbol),
        date(2026, 8, 11),
        date(2026, 8, 14),
    )


def _acquisition(marker: str) -> YahooSecurityPriceAcquisitionResult:
    provenance = YahooAcquisitionProvenance(
        source_url=f"https://example.invalid/{marker}",
        retrieved_at=_CHECKED_AT,
        sha256_hex="a" * 64,
        is_from_cache=False,
    )
    return YahooSecurityPriceAcquisitionResult((), provenance)


class RecordingSource:
    def __init__(
        self,
        outcomes: dict[str, YahooSecurityPriceAcquisitionResult | YahooSecurityPriceSourceError],
    ) -> None:
        self._outcomes = outcomes
        self.calls: list[tuple[YahooSecurityPriceRequest, datetime | None]] = []

    def acquire(
        self,
        request: YahooSecurityPriceRequest,
        checked_at: datetime | None = None,
    ) -> YahooSecurityPriceAcquisitionResult:
        self.calls.append((request, checked_at))
        outcome = self._outcomes[request.mapping.normalized_provider_symbol]
        if isinstance(outcome, YahooSecurityPriceSourceError):
            raise outcome
        return outcome


def test_deduplicates_normalized_requests_and_preserves_input_outcomes() -> None:
    first = _request("AKBNK", "AKBNK.IS")
    duplicate = _request(" AKBNK ", " akbnk.is ")
    other = _request("THYAO", "THYAO.IS")
    akbnk = _acquisition("akbnk")
    thyao = _acquisition("thyao")
    source = RecordingSource({"AKBNK.IS": akbnk, "THYAO.IS": thyao})

    result = acquire_yahoo_security_price_batch(
        (first, duplicate, other),
        source,
        checked_at=_CHECKED_AT,
    )

    assert [call[0] for call in source.calls] == [first, other]
    assert all(call[1] is _CHECKED_AT for call in source.calls)
    assert result.total == 3
    assert result.unique_request_count == 2
    assert len(result.successes) == 3
    assert result.failures == ()
    assert result.outcomes[0].request is first
    assert result.outcomes[1].request is duplicate
    assert result.outcomes[0].acquisition is result.outcomes[1].acquisition  # type: ignore[union-attr]


def test_isolates_typed_failure_and_reuses_it_for_duplicate_request() -> None:
    failed = _request("AKBNK", "AKBNK.IS")
    duplicate = _request("AKBNK", "akbnk.is")
    successful = _request("THYAO", "THYAO.IS")
    rate_limit = YahooSecurityPriceRateLimitError("rate limited", retry_after="60")
    thyao = _acquisition("thyao")
    source = RecordingSource({"AKBNK.IS": rate_limit, "THYAO.IS": thyao})

    result = acquire_yahoo_security_price_batch(
        (failed, successful, duplicate),
        source,
        checked_at=_CHECKED_AT,
    )

    assert [call[0] for call in source.calls] == [failed, successful]
    assert isinstance(result.outcomes[0], YahooSecurityPriceBatchFailure)
    assert isinstance(result.outcomes[1], YahooSecurityPriceBatchSuccess)
    assert isinstance(result.outcomes[2], YahooSecurityPriceBatchFailure)
    assert result.outcomes[0].error is rate_limit
    assert result.outcomes[2].error is rate_limit
    assert result.successes[0].request is successful
    assert [failure.request for failure in result.failures] == [failed, duplicate]


def test_does_not_swallow_unexpected_programming_error() -> None:
    request = _request("AKBNK", "AKBNK.IS")

    class BrokenSource:
        def acquire(self, request, checked_at=None):  # type: ignore[no-untyped-def]
            raise RuntimeError("unexpected bug")

    with pytest.raises(RuntimeError, match="unexpected bug"):
        acquire_yahoo_security_price_batch((request,), BrokenSource())


def test_consumes_generator_once() -> None:
    requests = [_request("AKBNK", "AKBNK.IS"), _request("THYAO", "THYAO.IS")]
    yielded = 0

    def generate():  # type: ignore[no-untyped-def]
        nonlocal yielded
        for request in requests:
            yielded += 1
            yield request

    source = RecordingSource({"AKBNK.IS": _acquisition("akbnk"), "THYAO.IS": _acquisition("thyao")})
    result = acquire_yahoo_security_price_batch(generate(), source)

    assert yielded == 2
    assert result.total == 2


def test_rejects_empty_or_invalid_batch_before_execution() -> None:
    source = RecordingSource({})
    with pytest.raises(YahooSecurityPriceBatchError, match="at least one"):
        acquire_yahoo_security_price_batch((), source)
    with pytest.raises(YahooSecurityPriceBatchError, match="must be"):
        acquire_yahoo_security_price_batch((_request("AKBNK", "AKBNK.IS"), object()), source)  # type: ignore[arg-type]
    assert source.calls == []


def test_rejects_non_utc_checked_at_before_execution() -> None:
    request = _request("AKBNK", "AKBNK.IS")
    source = RecordingSource({"AKBNK.IS": _acquisition("akbnk")})
    non_utc = datetime(2026, 8, 15, 12, tzinfo=timezone(timedelta(hours=3)))

    with pytest.raises(YahooSecurityPriceBatchError, match="UTC"):
        acquire_yahoo_security_price_batch((request,), source, checked_at=non_utc)
    assert source.calls == []
