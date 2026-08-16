"""Tests for source-backed point-in-time holdings and security-price alignment."""

from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    MissingHoldingsSnapshotError,
    NavlensValidationError,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    align_point_in_time_from_source,
)
from navlens._native import is_security_price_alignment_supported
from navlens.alignment import (
    InvalidPriceHistoryStartError,
    SecurityPriceSourceMismatchError,
)
from navlens.datasets import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)

PREDICTION_TIMESTAMP = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
PUBLICATION_TIMESTAMP = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
PRICING_AS_OF = date(2026, 1, 31)
START_DATE = date(2026, 1, 1)


class FakeRecordingSecurityPriceSource:
    """Recording test fake implementing the SecurityPriceSource protocol."""

    def __init__(
        self,
        source_id: str = "market",
        data: dict[str, tuple[SecurityPriceSnapshot, ...]] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self._source_id = source_id
        self._data = data or {}
        self._errors = errors or {}
        self.queries: list[SecurityPriceQuery] = []

    @property
    def source_id(self) -> str:
        return self._source_id

    def fetch_security_prices(
        self,
        query: SecurityPriceQuery,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        self.queries.append(query)
        if query.instrument_id in self._errors:
            raise self._errors[query.instrument_id]
        return self._data.get(query.instrument_id, ())


def policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        MarketDate(2026, 1, 31),
        2,
        5,
    )


def request(*, security_price_source_id: str = "market") -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        "AAL",
        PREDICTION_TIMESTAMP,
        "kap",
        security_price_source_id,
        policy(),
    )


def holdings_snapshot(
    positions: tuple[HoldingPosition, ...],
    *,
    source_id: str = "kap",
    published_at: datetime = PUBLICATION_TIMESTAMP,
) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=published_at,
        ingested_at=published_at,
        source_id=source_id,
        positions=positions,
    )


def price_snapshot(
    instrument_id: str,
    day: int,
    *,
    available_at: datetime = PUBLICATION_TIMESTAMP,
    currency: str = "TRY",
    adjustment: str = "total_return_adjusted",
    price: float = 10.0,
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            instrument_id,
            MarketDate(2026, 1, day),
            UnitPrice(price),
            CurrencyCode(currency),
            PriceAdjustment(adjustment),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="market",
    )


def equity(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def etf(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("exchange_traded_fund"), weight)


def cash(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("cash"), weight)


def test_source_id_mismatch_fails_before_io() -> None:
    source = FakeRecordingSecurityPriceSource(source_id="yahoo")
    holdings = holdings_snapshot((equity("GARAN", 0.5),))

    with pytest.raises(SecurityPriceSourceMismatchError) as captured:
        align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert "does not match" in str(captured.value)
    assert source.queries == []


def test_invalid_start_date_type_fails_before_io() -> None:
    source = FakeRecordingSecurityPriceSource()
    holdings = holdings_snapshot((equity("GARAN", 0.5),))

    with pytest.raises(InvalidPriceHistoryStartError) as captured:
        align_point_in_time_from_source(
            request(),
            [holdings],
            source,
            "2026-01-01",  # type: ignore[arg-type]
        )
    assert "must be an exact date instance" in str(captured.value)
    assert source.queries == []

    with pytest.raises(InvalidPriceHistoryStartError):
        align_point_in_time_from_source(
            request(),
            [holdings],
            source,
            MarketDate(2026, 1, 1),  # type: ignore[arg-type]
        )
    assert source.queries == []


def test_start_date_after_pricing_as_of_fails_before_io() -> None:
    source = FakeRecordingSecurityPriceSource()
    holdings = holdings_snapshot((equity("GARAN", 0.5),))
    invalid_start = date(2026, 2, 5)

    with pytest.raises(InvalidPriceHistoryStartError) as captured:
        align_point_in_time_from_source(request(), [holdings], source, invalid_start)

    assert "cannot be after pricing_as_of_date" in str(captured.value)
    assert source.queries == []


def test_missing_holdings_fails_before_io() -> None:
    source = FakeRecordingSecurityPriceSource()
    future_holdings = holdings_snapshot(
        (equity("GARAN", 0.5),),
        published_at=datetime(2026, 2, 1, 13, 0, tzinfo=UTC),
    )

    with pytest.raises(MissingHoldingsSnapshotError):
        align_point_in_time_from_source(request(), [future_holdings], source, START_DATE)

    assert source.queries == []


def test_unsupported_asset_classes_produce_zero_source_queries_and_typed_gaps() -> None:
    source = FakeRecordingSecurityPriceSource()
    holdings = holdings_snapshot(
        (
            cash("TRY_CASH", 0.1),
            HoldingPosition("REPO_01", AssetClass("repo"), 0.2),
            HoldingPosition("DEP_01", AssetClass("deposit"), 0.3),
            HoldingPosition("DERIV_01", AssetClass("derivative"), 0.4),
        )
    )

    result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert source.queries == []
    assert len(result.report.uncovered_listed) == 4
    for uncovered in result.report.uncovered_listed:
        assert uncovered.reason.kind == "unsupported_asset_class"


def test_supported_asset_classes_are_queried_with_exact_date_bounds() -> None:
    garan_prices = (price_snapshot("GARAN", 30), price_snapshot("GARAN", 31))
    gldtr_prices = (price_snapshot("GLDTR", 30), price_snapshot("GLDTR", 31))
    source = FakeRecordingSecurityPriceSource(data={"GARAN": garan_prices, "GLDTR": gldtr_prices})
    holdings = holdings_snapshot((equity("GARAN", 0.6), etf("GLDTR", 0.4)))

    result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert len(source.queries) == 2
    assert source.queries[0] == SecurityPriceQuery("GARAN", START_DATE, PRICING_AS_OF)
    assert source.queries[1] == SecurityPriceQuery("GLDTR", START_DATE, PRICING_AS_OF)
    assert result.report.covered_weight == pytest.approx(1.0)


def test_unmapped_instrument_on_supported_asset_raises_error() -> None:
    source = FakeRecordingSecurityPriceSource(
        errors={"GARAN": SecurityPriceUnmappedInstrumentError("no mapping for GARAN")}
    )
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    with pytest.raises(SecurityPriceUnmappedInstrumentError, match="no mapping for GARAN"):
        align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert len(source.queries) == 1


def test_unmapped_instrument_on_unsupported_asset_does_not_raise() -> None:
    source = FakeRecordingSecurityPriceSource(
        errors={"TRY_CASH": SecurityPriceUnmappedInstrumentError("should not be called")}
    )
    holdings = holdings_snapshot((cash("TRY_CASH", 1.0),))

    result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert source.queries == []
    assert len(result.report.uncovered_listed) == 1
    assert result.report.uncovered_listed[0].reason.kind == "unsupported_asset_class"


def test_duplicate_holding_queries_source_once_then_fails_in_rust() -> None:
    source = FakeRecordingSecurityPriceSource(
        data={"GARAN": (price_snapshot("GARAN", 30), price_snapshot("GARAN", 31))}
    )
    holdings = holdings_snapshot((equity("GARAN", 0.3), equity("GARAN", 0.2)))

    with pytest.raises(NavlensValidationError, match="duplicate holding"):
        align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert len(source.queries) == 1
    assert source.queries[0].instrument_id == "GARAN"


def test_preserves_first_encountered_instrument_order() -> None:
    source = FakeRecordingSecurityPriceSource()
    holdings = holdings_snapshot(
        (
            equity("THYAO", 0.2),
            equity("AKBNK", 0.2),
            cash("TRY_CASH", 0.1),
            equity("SISE", 0.2),
            equity("THYAO", 0.1),
            equity("AKBNK", 0.1),
        )
    )

    with pytest.raises(NavlensValidationError, match="duplicate holding"):
        align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert [q.instrument_id for q in source.queries] == ["THYAO", "AKBNK", "SISE"]


def test_generator_inputs_consumed_once() -> None:
    garan_prices = (price_snapshot("GARAN", 30), price_snapshot("GARAN", 31))
    source = FakeRecordingSecurityPriceSource(data={"GARAN": garan_prices})
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    def holdings_gen() -> Iterator[HoldingSnapshot]:
        yield holdings

    result = align_point_in_time_from_source(request(), holdings_gen(), source, START_DATE)

    assert result.holdings_snapshot == holdings
    assert result.report.covered_weight == pytest.approx(1.0)


def test_multiple_revisions_preserved_and_resolved_by_prediction_timestamp() -> None:
    earlier_available = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    later_available = datetime(2026, 2, 1, 14, 0, tzinfo=UTC)

    rev1_31 = price_snapshot("GARAN", 31, available_at=earlier_available, price=10.0)
    rev2_31 = price_snapshot("GARAN", 31, available_at=later_available, price=20.0)
    obs_30 = price_snapshot("GARAN", 30, available_at=earlier_available, price=9.0)

    source = FakeRecordingSecurityPriceSource(data={"GARAN": (rev1_31, rev2_31, obs_30)})
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert result.selected_price_snapshots == (obs_30, rev1_31)
    assert result.report.covered[0].series.observations[-1].price.value == 10.0


def test_empty_source_result_becomes_missing_price_series_coverage_gap() -> None:
    source = FakeRecordingSecurityPriceSource(data={"GARAN": ()})
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert len(source.queries) == 1
    assert result.report.covered_weight == pytest.approx(0.0)
    assert len(result.report.uncovered_listed) == 1
    assert result.report.uncovered_listed[0].reason.kind == "missing_price_series"


def test_source_operational_errors_propagate_unchanged() -> None:
    source_unavail = FakeRecordingSecurityPriceSource(
        errors={"GARAN": SecurityPriceSourceUnavailableError("network down")}
    )
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    with pytest.raises(SecurityPriceSourceUnavailableError, match="network down"):
        align_point_in_time_from_source(request(), [holdings], source_unavail, START_DATE)

    source_corrupt = FakeRecordingSecurityPriceSource(
        errors={"GARAN": SecurityPriceCorruptedSourceDataError("corrupted schema")}
    )
    with pytest.raises(SecurityPriceCorruptedSourceDataError, match="corrupted schema"):
        align_point_in_time_from_source(request(), [holdings], source_corrupt, START_DATE)


def test_programming_errors_propagate_unchanged() -> None:
    class BrokenSource:
        @property
        def source_id(self) -> str:
            return "market"

    broken = BrokenSource()
    holdings = holdings_snapshot((equity("GARAN", 1.0),))

    with pytest.raises(AttributeError):
        align_point_in_time_from_source(
            request(),
            [holdings],
            broken,  # type: ignore[arg-type]
            START_DATE,
        )


def test_parity_between_direct_and_source_backed_alignment() -> None:
    garan_prices = (price_snapshot("GARAN", 30), price_snapshot("GARAN", 31))
    akbnk_prices = (price_snapshot("AKBNK", 30), price_snapshot("AKBNK", 31))
    holdings = holdings_snapshot(
        (
            equity("GARAN", 0.5),
            equity("AKBNK", 0.3),
            cash("TRY_CASH", 0.2),
        )
    )
    all_snapshots = (*garan_prices, *akbnk_prices)
    source = FakeRecordingSecurityPriceSource(data={"GARAN": garan_prices, "AKBNK": akbnk_prices})

    direct_result = align_point_in_time(request(), [holdings], all_snapshots)
    source_result = align_point_in_time_from_source(request(), [holdings], source, START_DATE)

    assert source_result.holdings_snapshot == direct_result.holdings_snapshot
    assert source_result.selected_price_snapshots == direct_result.selected_price_snapshots
    assert source_result.report.covered_weight == direct_result.report.covered_weight
    assert source_result.report.declared_weight == direct_result.report.declared_weight
    assert (
        source_result.report.uncovered_listed_weight == direct_result.report.uncovered_listed_weight
    )
    assert source_result.report.unrepresented_weight == direct_result.report.unrepresented_weight
    assert [c.holding.instrument_id for c in source_result.report.covered] == [
        c.holding.instrument_id for c in direct_result.report.covered
    ]
    assert [u.holding.instrument_id for u in source_result.report.uncovered_listed] == [
        u.holding.instrument_id for u in direct_result.report.uncovered_listed
    ]


def test_is_security_price_alignment_supported_internal_predicate() -> None:
    assert is_security_price_alignment_supported(AssetClass("equity")) is True
    assert is_security_price_alignment_supported(AssetClass("exchange_traded_fund")) is True
    assert is_security_price_alignment_supported(AssetClass("debt_security")) is False
    assert is_security_price_alignment_supported(AssetClass("repo")) is False
    assert is_security_price_alignment_supported(AssetClass("deposit")) is False
    assert is_security_price_alignment_supported(AssetClass("investment_fund")) is False
    assert is_security_price_alignment_supported(AssetClass("precious_metal")) is False
    assert is_security_price_alignment_supported(AssetClass("derivative")) is False
    assert is_security_price_alignment_supported(AssetClass("cash")) is False
    assert is_security_price_alignment_supported(AssetClass("other")) is False
