"""Coverage, gap, and skip tests for source-backed historical FX reconciliation."""

from datetime import date

import pytest
from navlens import MarketDate
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRecord,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedFxReconciliationRecord,
    build_historical_fx_reconciliation_dataset_from_security_price_source,
)
from tests.historical_fx_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_cash_position,
    make_deposit_position,
    make_derivative_position,
    make_equity_position,
    make_fund_unit_price_snapshot,
    make_fx_historical_request,
    make_fx_rate_snapshot,
    make_holding_snapshot,
    make_repo_position,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def test_same_currency_holding_requires_no_fx_evidence() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    # GARAN is in TRY (fund base currency), no FX rates provided at all
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("GARAN", 1.0),),
        )
    ]
    prices = {
        "GARAN": (
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz, currency="TRY"),
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz, currency="TRY"),
        )
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],  # Zero FX snapshots
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.return_coverage == pytest.approx(1.0)
    assert rec.observed_portfolio_contribution == pytest.approx(0.1)


def test_missing_fx_snapshot_produces_typed_return_gap() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    prices = {
        "AAPL": (
            make_security_price_snapshot("AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD"),
            make_security_price_snapshot("AAPL", MarketDate(2026, 1, 2), 105.0, tz, currency="USD"),
        )
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz),
    ]

    # No FX rate provided for USD/TRY
    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.return_coverage == pytest.approx(0.0)
    gaps = rec.result.contribution.contribution_result.return_gaps
    assert len(gaps) == 1
    assert gaps[0].reason.kind == "missing_direct_fx_candidate"


def test_stale_fx_snapshot_produces_reduced_coverage() -> None:
    prediction_time = make_utc_timestamp(2026, 1, 10)
    req = make_fx_historical_request(
        MarketDate(2026, 1, 9),
        MarketDate(2026, 1, 10),
        prediction_time,
    )
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 9),
            prediction_time,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    prices = {
        "AAPL": (
            make_security_price_snapshot(
                "AAPL", MarketDate(2026, 1, 9), 100.0, prediction_time, currency="USD"
            ),
            make_security_price_snapshot(
                "AAPL", MarketDate(2026, 1, 10), 105.0, prediction_time, currency="USD"
            ),
        )
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    # Stale FX rate (20 days old vs 5 day max staleness)
    stale_fx = make_fx_rate_snapshot("USD", "TRY", MarketDate(2025, 12, 20), 30.0, prediction_time)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 9), 10.0, prediction_time),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 10), 10.5, prediction_time),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [stale_fx],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.return_coverage == pytest.approx(0.0)
    gaps = rec.result.contribution.contribution_result.return_gaps
    assert len(gaps) == 1
    assert gaps[0].reason.kind == "stale_fx_start_observation"


def test_unsupported_asset_classes_produce_zero_source_queries() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (
                make_cash_position("TRY_CASH", 0.25),
                make_repo_position("REPO_1", 0.25),
                make_deposit_position("DEP_1", 0.25),
                make_derivative_position("DERIV_1", 0.25),
            ),
        )
    ]
    source = FakeRecordingSecurityPriceSource()
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 0
    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.return_coverage == pytest.approx(0.0)


def test_missing_holdings_yields_typed_skip_with_zero_source_queries() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    source = FakeRecordingSecurityPriceSource()
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        [],
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 0
    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedFxReconciliationRecord)
    assert isinstance(rec.reason, MissingHoldingsSkip)
    assert rec.request is req


def test_missing_start_fund_price_yields_typed_skip() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    source = FakeRecordingSecurityPriceSource(
        data={
            "AAPL": (
                make_security_price_snapshot(
                    "AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD"
                ),
                make_security_price_snapshot(
                    "AAPL", MarketDate(2026, 1, 2), 105.0, tz, currency="USD"
                ),
            )
        }
    )
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz)]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedFxReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 1)


def test_missing_end_fund_price_yields_typed_skip() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    source = FakeRecordingSecurityPriceSource(
        data={
            "AAPL": (
                make_security_price_snapshot(
                    "AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD"
                ),
                make_security_price_snapshot(
                    "AAPL", MarketDate(2026, 1, 2), 105.0, tz, currency="USD"
                ),
            )
        }
    )
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedFxReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 2)
