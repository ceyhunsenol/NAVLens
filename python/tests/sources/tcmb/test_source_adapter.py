"""Tests for the provider-neutral TCMB FX-rate source adapter."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    MarketCalendar,
    MarketDate,
)
from navlens.datasets import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateSnapshot,
    FxRateSourceUnavailableError,
    FxRateUnmappedPairError,
)
from navlens.sources.tcmb import (
    TCMB_SOURCE_ID,
    TcmbAcquisitionContext,
    TcmbCacheMissError,
    TcmbCachePolicy,
    TcmbFxRateSource,
    TcmbHttpResponse,
    TcmbOrchestrationError,
    TcmbOrchestrationSnapshotLoader,
    TcmbTransportError,
)


class RecordingLoader:
    def __init__(
        self,
        snapshots_by_date: dict[str, tuple[FxRateSnapshot, ...]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.snapshots_by_date = snapshots_by_date or {}
        self.error = error
        self.requested_dates: list[MarketDate] = []

    def load(self, market_date: MarketDate) -> tuple[FxRateSnapshot, ...]:
        self.requested_dates.append(market_date)
        if self.error is not None:
            raise self.error
        return self.snapshots_by_date.get(str(market_date), ())


class StaticResponseClient:
    def __init__(self, response: TcmbHttpResponse) -> None:
        self.response = response
        self.requested_dates: list[date | None] = []

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
        self.requested_dates.append(archive_date)
        return self.response


def make_snapshot(
    market_date: MarketDate,
    rate: float,
    *,
    base: str = "USD",
    quote: str = "TRY",
    kind: str = "non_cash_buying",
    source_id: str = TCMB_SOURCE_ID,
    available_hour: int = 13,
) -> FxRateSnapshot:
    available_at = datetime(
        int(str(market_date)[:4]),
        int(str(market_date)[5:7]),
        int(str(market_date)[8:]),
        available_hour,
        tzinfo=UTC,
    )
    return FxRateSnapshot(
        observation=FxRateObservation(
            CurrencyPair(CurrencyCode(base), CurrencyCode(quote)),
            market_date,
            FxRate(rate),
            FxRateKind(kind),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def make_query(
    start_date: date,
    end_date: date,
    *,
    base: str = "USD",
    quote: str = "TRY",
    kind: str = "non_cash_buying",
) -> FxRateQuery:
    return FxRateQuery(
        CurrencyPair(CurrencyCode(base), CurrencyCode(quote)),
        FxRateKind(kind),
        start_date,
        end_date,
    )


def test_source_filters_exact_pair_and_kind_while_preserving_revision_identity() -> None:
    first = make_snapshot(MarketDate(2026, 8, 17), 40.0)
    revision = make_snapshot(MarketDate(2026, 8, 17), 40.2, available_hour=14)
    selling = make_snapshot(MarketDate(2026, 8, 17), 40.4, kind="non_cash_selling")
    loader = RecordingLoader({"2026-08-17": (first, revision, selling)})
    source = TcmbFxRateSource(MarketCalendar(), loader)

    snapshots = source.fetch_fx_rates(make_query(date(2026, 8, 17), date(2026, 8, 17)))

    assert snapshots == (first, revision)
    assert snapshots[0] is first
    assert snapshots[1] is revision


def test_source_skips_closed_calendar_dates_without_loading() -> None:
    loader = RecordingLoader()
    source = TcmbFxRateSource(MarketCalendar(), loader)

    snapshots = source.fetch_fx_rates(make_query(date(2026, 8, 15), date(2026, 8, 16)))

    assert snapshots == ()
    assert loader.requested_dates == []


def test_source_rejects_non_try_direction_before_loading() -> None:
    loader = RecordingLoader()
    source = TcmbFxRateSource(MarketCalendar(), loader)

    with pytest.raises(FxRateUnmappedPairError, match="quoted in TRY"):
        source.fetch_fx_rates(
            make_query(date(2026, 8, 17), date(2026, 8, 17), quote="USD", base="TRY")
        )

    assert loader.requested_dates == []


@pytest.mark.parametrize(
    "snapshots",
    [
        [make_snapshot(MarketDate(2026, 8, 17), 40.0)],
        (make_snapshot(MarketDate(2026, 8, 17), 40.0, source_id="foreign"),),
        (make_snapshot(MarketDate(2026, 8, 18), 40.0),),
    ],
)
def test_source_rejects_corrupted_loader_contract(snapshots: object) -> None:
    loader = RecordingLoader({"2026-08-17": snapshots})  # type: ignore[dict-item]
    source = TcmbFxRateSource(MarketCalendar(), loader)

    with pytest.raises(FxRateCorruptedSourceDataError):
        source.fetch_fx_rates(make_query(date(2026, 8, 17), date(2026, 8, 17)))


def test_cache_miss_maps_to_provider_neutral_unavailable_error() -> None:
    loader = RecordingLoader(error=TcmbCacheMissError("missing cached day"))
    source = TcmbFxRateSource(MarketCalendar(), loader)

    with pytest.raises(FxRateSourceUnavailableError) as exc_info:
        source.fetch_fx_rates(make_query(date(2026, 8, 17), date(2026, 8, 17)))

    assert isinstance(exc_info.value.__cause__, TcmbCacheMissError)


def test_transport_cause_maps_to_provider_neutral_unavailable_error() -> None:
    error = _orchestration_error_from(TcmbTransportError("offline"))
    source = TcmbFxRateSource(MarketCalendar(), RecordingLoader(error=error))

    with pytest.raises(FxRateSourceUnavailableError) as exc_info:
        source.fetch_fx_rates(make_query(date(2026, 8, 17), date(2026, 8, 17)))

    assert exc_info.value.__cause__ is error


def test_unclassified_orchestration_contract_error_propagates_unchanged() -> None:
    error = TcmbOrchestrationError("invalid adapter configuration")
    source = TcmbFxRateSource(MarketCalendar(), RecordingLoader(error=error))

    with pytest.raises(TcmbOrchestrationError) as exc_info:
        source.fetch_fx_rates(make_query(date(2026, 8, 17), date(2026, 8, 17)))

    assert exc_info.value is error


def test_real_orchestration_loader_refreshes_then_reads_cache(tmp_path: Path) -> None:
    archive_date = date(2024, 1, 2)
    response = TcmbHttpResponse(
        body=_daily_rates_xml(),
        source_url="https://example.test/tcmb.xml",
        requested_archive_date=archive_date,
    )
    client = StaticResponseClient(response)

    def context_factory(_: MarketDate) -> TcmbAcquisitionContext:
        return TcmbAcquisitionContext(
            client=client,
            calendar=MarketCalendar(),
            retrieved_at=datetime(2024, 1, 2, 16, 0, tzinfo=UTC),
        )

    refresh_loader = TcmbOrchestrationSnapshotLoader(
        tmp_path,
        TcmbCachePolicy.refresh,
        context_factory,
    )
    refresh_source = TcmbFxRateSource(MarketCalendar(), refresh_loader)
    refreshed = refresh_source.fetch_fx_rates(make_query(archive_date, archive_date))

    cached_loader = TcmbOrchestrationSnapshotLoader(tmp_path, TcmbCachePolicy.cache_only)
    cached_source = TcmbFxRateSource(MarketCalendar(), cached_loader)
    cached = cached_source.fetch_fx_rates(make_query(archive_date, archive_date))

    assert len(refreshed) == 1
    assert refreshed[0].observation.rate == FxRate(30.0)
    assert len(cached) == 1
    assert cached[0].observation.rate == FxRate(30.0)
    assert client.requested_dates == [archive_date]


def test_loader_requires_context_factory_only_for_network_policies(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be omitted"):
        TcmbOrchestrationSnapshotLoader(
            tmp_path,
            TcmbCachePolicy.cache_only,
            lambda _: None,  # type: ignore[arg-type,return-value]
        )
    with pytest.raises(ValueError, match="is required"):
        TcmbOrchestrationSnapshotLoader(tmp_path, TcmbCachePolicy.refresh)


def _orchestration_error_from(cause: Exception) -> TcmbOrchestrationError:
    try:
        raise cause
    except Exception as error:
        try:
            raise TcmbOrchestrationError("wrapped") from error
        except TcmbOrchestrationError as wrapped:
            return wrapped


def _daily_rates_xml() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="02.01.2024" Date="02.01.2024" Bulten_No="2024/1">
  <Currency CrossOrder="0" Kod="USD" CurrencyCode="USD">
    <Unit>1</Unit>
    <Isim>US DOLLAR</Isim>
    <CurrencyName>US DOLLAR</CurrencyName>
    <ForexBuying>30.00</ForexBuying>
    <ForexSelling>30.50</ForexSelling>
    <BanknoteBuying>29.90</BanknoteBuying>
    <BanknoteSelling>30.60</BanknoteSelling>
  </Currency>
</Tarih_Date>"""
