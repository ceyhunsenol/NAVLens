"""Error, edge case, and fail-fast tests for source-backed historical reconciliation builder."""

from datetime import date

import pytest
from navlens import MarketDate, NavlensValidationError
from navlens.alignment import (
    InvalidPriceHistoryStartError,
    SecurityPriceSourceMismatchError,
)
from navlens.datasets import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)
from navlens.reconciliation.historical import (
    DecreasingPeriodError,
    DuplicatePeriodError,
    build_historical_reconciliation_dataset_from_source,
)
from tests.historical_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_equity_position,
    make_fund_unit_price_snapshot,
    make_historical_request,
    make_holding_snapshot,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def test_decreasing_period_fails_before_any_provider_io() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 1)

    req1 = make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz1)
    req2 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz2)

    source = FakeRecordingSecurityPriceSource()
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz1, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz1)]

    with pytest.raises(DecreasingPeriodError):
        build_historical_reconciliation_dataset_from_source(
            [req1, req2],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert source.queries == []


def test_duplicate_period_fails_before_any_provider_io() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req1 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    req2 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    source = FakeRecordingSecurityPriceSource()
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(DuplicatePeriodError):
        build_historical_reconciliation_dataset_from_source(
            [req1, req2],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert source.queries == []


def test_source_id_mismatch_fails_fast_before_io() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(
        MarketDate(2026, 1, 1),
        MarketDate(2026, 1, 2),
        tz,
        security_price_source_id="src_expected",
    )
    source = FakeRecordingSecurityPriceSource(source_id="src_actual")
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(SecurityPriceSourceMismatchError, match="does not match"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert source.queries == []


def test_invalid_price_history_start_date_type_fails_before_io() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    source = FakeRecordingSecurityPriceSource()
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(InvalidPriceHistoryStartError, match="must be an exact date instance"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date="2026-01-01",  # type: ignore[arg-type]
        )

    assert source.queries == []

    with pytest.raises(InvalidPriceHistoryStartError, match="must be an exact date instance"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=MarketDate(2026, 1, 1),  # type: ignore[arg-type]
        )

    assert source.queries == []


def test_price_history_start_date_after_pricing_as_of_fails_before_io() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    source = FakeRecordingSecurityPriceSource()
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(
        InvalidPriceHistoryStartError,
        match="cannot be after pricing_as_of_date",
    ):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 10),
        )

    assert source.queries == []


def test_duplicate_holding_instruments_produce_single_query_then_fail_in_rust() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("GARAN", 0.5), make_equity_position("GARAN", 0.5)),
        )
    ]
    source = FakeRecordingSecurityPriceSource(
        data={
            "GARAN": (
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz),
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz),
            )
        }
    )
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    with pytest.raises(NavlensValidationError, match="duplicate holding"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert len(source.queries) == 1
    assert source.queries[0].instrument_id == "GARAN"


def test_source_unmapped_instrument_propagates_fail_fast() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("UNKNOWN", 1.0),))
    ]
    source = FakeRecordingSecurityPriceSource(
        errors={"UNKNOWN": SecurityPriceUnmappedInstrumentError("unmapped instrument")}
    )
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(SecurityPriceUnmappedInstrumentError, match="unmapped instrument"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert len(source.queries) == 1


def test_source_unavailable_propagates_fail_fast() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    source = FakeRecordingSecurityPriceSource(
        errors={"GARAN": SecurityPriceSourceUnavailableError("source offline")}
    )
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(SecurityPriceSourceUnavailableError, match="source offline"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert len(source.queries) == 1


def test_source_corrupted_data_propagates_fail_fast() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    source = FakeRecordingSecurityPriceSource(
        errors={"GARAN": SecurityPriceCorruptedSourceDataError("corrupted schema")}
    )
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(SecurityPriceCorruptedSourceDataError, match="corrupted schema"):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert len(source.queries) == 1


def test_programming_contract_errors_propagate_unchanged() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    class NonConformingSource:
        @property
        def source_id(self) -> str:
            return "src_p"

    broken_source = NonConformingSource()
    holdings = [
        make_holding_snapshot(MarketDate(2026, 1, 1), tz, (make_equity_position("GARAN", 1.0),))
    ]
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    with pytest.raises(AttributeError):
        build_historical_reconciliation_dataset_from_source(
            [req],
            holdings,
            broken_source,  # type: ignore[arg-type]
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )
