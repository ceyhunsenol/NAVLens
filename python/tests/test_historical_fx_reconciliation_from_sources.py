"""Tests for fully source-backed historical FX reconciliation orchestration."""

from datetime import date

import pytest
from navlens import MarketDate
from navlens.alignment import FxRateSourceMismatchError
from navlens.datasets import FxRateQuery, FxRateSourceUnavailableError
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRecord,
    build_historical_fx_reconciliation_dataset,
    build_historical_fx_reconciliation_dataset_from_sources,
)
from tests.historical_fx_reconciliation_source_fixtures import (
    FakeRecordingFxRateSource,
    FakeRecordingSecurityPriceSource,
    make_equity_position,
    make_fund_unit_price_snapshot,
    make_fx_historical_request,
    make_fx_rate_snapshot,
    make_holding_snapshot,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def _source_backed_case() -> tuple[object, list[object], list[object], list[object], list[object]]:
    timestamp = make_utc_timestamp(2026, 1, 2)
    request = make_fx_historical_request(
        MarketDate(2026, 1, 1),
        MarketDate(2026, 1, 2),
        timestamp,
    )
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            timestamp,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    prices = [
        make_security_price_snapshot(
            "AAPL", MarketDate(2026, 1, 1), 100.0, timestamp, currency="USD"
        ),
        make_security_price_snapshot(
            "AAPL", MarketDate(2026, 1, 2), 105.0, timestamp, currency="USD"
        ),
    ]
    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, timestamp),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 31.0, timestamp),
    ]
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, timestamp),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.85, timestamp),
    ]
    return request, holdings, prices, fx_rates, fund_prices


def test_fully_source_backed_builder_matches_snapshot_builder() -> None:
    request, holdings, prices, fx_rates, fund_prices = _source_backed_case()
    security_source = FakeRecordingSecurityPriceSource(data={"AAPL": tuple(prices)})
    fx_source = FakeRecordingFxRateSource(data={("USD", "TRY", "non_cash_buying"): tuple(fx_rates)})

    expected = build_historical_fx_reconciliation_dataset(
        [request], holdings, prices, fx_rates, fund_prices
    )
    actual = build_historical_fx_reconciliation_dataset_from_sources(
        [request],
        holdings,
        security_source,
        fx_source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(actual.outcomes) == 1
    actual_record = actual.outcomes[0]
    expected_record = expected.outcomes[0]
    assert isinstance(actual_record, HistoricalFxReconciliationRecord)
    assert isinstance(expected_record, HistoricalFxReconciliationRecord)
    assert actual_record.request is expected_record.request
    assert actual_record.published_fund_return == pytest.approx(
        expected_record.published_fund_return
    )
    assert actual_record.observed_portfolio_contribution == pytest.approx(
        expected_record.observed_portfolio_contribution
    )
    assert actual_record.return_coverage == pytest.approx(expected_record.return_coverage)
    assert actual_record.reconciliation_residual == pytest.approx(
        expected_record.reconciliation_residual
    )
    assert actual_record.result.contribution.selected_fx_snapshots == tuple(fx_rates)


def test_fx_query_includes_staleness_window_and_exact_contract_fields() -> None:
    request, holdings, prices, fx_rates, fund_prices = _source_backed_case()
    security_source = FakeRecordingSecurityPriceSource(data={"AAPL": tuple(prices)})
    fx_source = FakeRecordingFxRateSource(data={("USD", "TRY", "non_cash_buying"): tuple(fx_rates)})

    build_historical_fx_reconciliation_dataset_from_sources(
        [request],
        holdings,
        security_source,
        fx_source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert fx_source.queries == [
        FxRateQuery(
            pair=fx_rates[0].observation.pair,
            kind=fx_rates[0].observation.kind,
            start_date=date(2025, 12, 27),
            end_date=date(2026, 1, 2),
        )
    ]


def test_fx_source_identity_mismatch_fails_before_fx_fetch() -> None:
    request, holdings, prices, _, fund_prices = _source_backed_case()
    security_source = FakeRecordingSecurityPriceSource(data={"AAPL": tuple(prices)})
    fx_source = FakeRecordingFxRateSource(source_id="another_fx_source")

    with pytest.raises(FxRateSourceMismatchError, match="does not match"):
        build_historical_fx_reconciliation_dataset_from_sources(
            [request],
            holdings,
            security_source,
            fx_source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert fx_source.queries == []


def test_fx_source_failure_propagates_without_becoming_a_coverage_gap() -> None:
    request, holdings, prices, _, fund_prices = _source_backed_case()
    security_source = FakeRecordingSecurityPriceSource(data={"AAPL": tuple(prices)})
    failure = FxRateSourceUnavailableError("FX backend unavailable")
    fx_source = FakeRecordingFxRateSource(error=failure)

    with pytest.raises(FxRateSourceUnavailableError, match="FX backend unavailable") as captured:
        build_historical_fx_reconciliation_dataset_from_sources(
            [request],
            holdings,
            security_source,
            fx_source,
            fund_prices,
            price_history_start_date=date(2026, 1, 1),
        )

    assert captured.value is failure


def test_base_currency_only_portfolio_does_not_query_fx_source() -> None:
    request, holdings, _, _, fund_prices = _source_backed_case()
    timestamp = make_utc_timestamp(2026, 1, 2)
    try_prices = (
        make_security_price_snapshot(
            "AAPL", MarketDate(2026, 1, 1), 100.0, timestamp, currency="TRY"
        ),
        make_security_price_snapshot(
            "AAPL", MarketDate(2026, 1, 2), 105.0, timestamp, currency="TRY"
        ),
    )
    security_source = FakeRecordingSecurityPriceSource(data={"AAPL": try_prices})
    fx_source = FakeRecordingFxRateSource(error=FxRateSourceUnavailableError("must not run"))

    dataset = build_historical_fx_reconciliation_dataset_from_sources(
        [request],
        holdings,
        security_source,
        fx_source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert isinstance(dataset.outcomes[0], HistoricalFxReconciliationRecord)
    assert fx_source.queries == []
