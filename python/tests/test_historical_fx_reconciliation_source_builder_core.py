"""Core integration tests for source-backed historical FX reconciliation dataset builder."""

from collections.abc import Iterator
from datetime import date

import pytest
from navlens import MarketDate
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceQuery,
)
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRecord,
    HistoricalFxReconciliationRequest,
    build_historical_fx_reconciliation_dataset_from_security_price_source,
)
from tests.historical_fx_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_equity_position,
    make_etf_position,
    make_fund_unit_price_snapshot,
    make_fx_alignment_policy,
    make_fx_historical_request,
    make_fx_rate_snapshot,
    make_holding_snapshot,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def test_single_period_successful_fx_reconciliation() -> None:
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
    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 31.0, tz),
    ]
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.85, tz),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.request is req
    assert rec.result.start_snapshot is fund_prices[0]
    assert rec.result.end_snapshot is fund_prices[1]
    assert rec.result.fund_price_source_id == "src_f"
    assert rec.return_coverage == pytest.approx(1.0)
    # Effective USD asset return = (1.05)*(31/30) - 1 = 1.085 - 1 = 0.085
    assert rec.observed_portfolio_contribution == pytest.approx(0.085)
    assert rec.published_fund_return == pytest.approx(0.085)
    assert rec.reconciliation_residual == pytest.approx(0.0)


def test_multiple_chronological_periods_and_fx_result_ordering() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_fx_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("AAPL", 1.0),),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("AAPL", 1.0),),
        ),
    ]
    prices = {
        "AAPL": (
            make_security_price_snapshot(
                "AAPL", MarketDate(2026, 1, 1), 100.0, tz1, currency="USD"
            ),
            make_security_price_snapshot(
                "AAPL", MarketDate(2026, 1, 2), 105.0, tz1, currency="USD"
            ),
            make_security_price_snapshot(
                "AAPL", MarketDate(2026, 1, 3), 110.25, tz2, currency="USD"
            ),
        )
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz1),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 30.0, tz1),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 3), 30.0, tz2),
    ]
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 11.025, tz2),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req1, req2],
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 2
    rec1, rec2 = dataset.outcomes
    assert isinstance(rec1, HistoricalFxReconciliationRecord)
    assert isinstance(rec2, HistoricalFxReconciliationRecord)
    assert rec1.request is req1
    assert rec2.request is req2
    assert rec1.return_coverage == pytest.approx(1.0)
    assert rec2.return_coverage == pytest.approx(1.0)
    assert rec1.observed_portfolio_contribution == pytest.approx(0.05)
    assert rec2.observed_portfolio_contribution == pytest.approx(0.05)


def test_exact_query_date_bounds_and_instrument_fields() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_fx_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("AAPL", 0.5), make_etf_position("SPY", 0.5)),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("MSFT", 1.0),),
        ),
    ]
    source = FakeRecordingSecurityPriceSource()
    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz1),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 30.0, tz1),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 3), 30.0, tz2),
    ]
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 11.0, tz2),
    ]

    build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req1, req2],
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2025, 12, 20),
    )

    assert len(source.queries) == 3
    assert source.queries[0] == SecurityPriceQuery(
        instrument_id="AAPL",
        start_date=date(2025, 12, 20),
        end_date=date(2026, 1, 2),
    )
    assert source.queries[1] == SecurityPriceQuery(
        instrument_id="SPY",
        start_date=date(2025, 12, 20),
        end_date=date(2026, 1, 2),
    )
    assert source.queries[2] == SecurityPriceQuery(
        instrument_id="MSFT",
        start_date=date(2025, 12, 20),
        end_date=date(2026, 1, 3),
    )


def test_minimum_observations_3_and_prior_history_success() -> None:
    tz = make_utc_timestamp(2026, 1, 3)
    policy_3_obs = make_fx_alignment_policy(
        MarketDate(2026, 1, 3),
        minimum_observations=3,
    )
    req = make_fx_historical_request(
        MarketDate(2026, 1, 2),
        MarketDate(2026, 1, 3),
        tz,
        policy=policy_3_obs,
    )
    holding = make_holding_snapshot(
        MarketDate(2026, 1, 2),
        tz,
        (make_equity_position("AAPL", 1.0),),
    )

    # 3 observations: 2026-01-01, 2026-01-02, 2026-01-03
    p1 = make_security_price_snapshot("AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD")
    p2 = make_security_price_snapshot("AAPL", MarketDate(2026, 1, 2), 105.0, tz, currency="USD")
    p3 = make_security_price_snapshot("AAPL", MarketDate(2026, 1, 3), 110.25, tz, currency="USD")

    source = FakeRecordingSecurityPriceSource(data={"AAPL": (p1, p2, p3)})
    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 30.0, tz),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 3), 31.0, tz),
    ]
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 10.85, tz),
    ]

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        [holding],
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 1
    assert source.queries[0].start_date == date(2026, 1, 1)
    assert source.queries[0].start_date != date(2026, 1, 2)
    assert source.queries[0].end_date == date(2026, 1, 3)

    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert rec.return_coverage == pytest.approx(1.0)


def test_generator_inputs_consumed_once() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holding = make_holding_snapshot(
        MarketDate(2026, 1, 1),
        tz,
        (make_equity_position("AAPL", 1.0),),
    )
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
    fx = make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz)
    fund_p1 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz)
    fund_p2 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz)

    def req_gen() -> Iterator[HistoricalFxReconciliationRequest]:
        yield req

    def holdings_gen() -> Iterator[HoldingSnapshot]:
        yield holding

    def fx_gen() -> Iterator[FxRateSnapshot]:
        yield fx

    def fund_gen() -> Iterator[FundUnitPriceSnapshot]:
        yield fund_p1
        yield fund_p2

    dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        req_gen(),
        holdings_gen(),
        source,
        fx_gen(),
        fund_gen(),
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    assert isinstance(dataset.outcomes[0], HistoricalFxReconciliationRecord)


def test_source_builder_materialization_order() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holding = make_holding_snapshot(
        MarketDate(2026, 1, 1),
        tz,
        (make_equity_position("AAPL", 1.0),),
    )
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
    fx = make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz)
    fund_p1 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz)
    fund_p2 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz)

    consumption_order: list[str] = []

    def req_iter() -> Iterator[HistoricalFxReconciliationRequest]:
        consumption_order.append("requests")
        yield req

    def holdings_iter() -> Iterator[HoldingSnapshot]:
        consumption_order.append("holdings")
        yield holding

    def fx_iter() -> Iterator[FxRateSnapshot]:
        consumption_order.append("fx_rates")
        yield fx

    def fund_iter() -> Iterator[FundUnitPriceSnapshot]:
        consumption_order.append("fund_prices")
        yield fund_p1
        yield fund_p2

    build_historical_fx_reconciliation_dataset_from_security_price_source(
        req_iter(),
        holdings_iter(),
        source,
        fx_iter(),
        fund_iter(),
        price_history_start_date=date(2026, 1, 1),
    )

    assert consumption_order == ["requests", "holdings", "fx_rates", "fund_prices"]


def test_public_export_boundary() -> None:
    import navlens
    import navlens.reconciliation
    import navlens.reconciliation.historical

    assert hasattr(
        navlens.reconciliation.historical,
        "build_historical_fx_reconciliation_dataset_from_security_price_source",
    )
    assert not hasattr(
        navlens,
        "build_historical_fx_reconciliation_dataset_from_security_price_source",
    )
    assert not hasattr(
        navlens.reconciliation,
        "build_historical_fx_reconciliation_dataset_from_security_price_source",
    )
    assert not hasattr(
        navlens.reconciliation.historical,
        "_execute_historical_fx_reconciliation",
    )
    assert not hasattr(
        navlens.reconciliation.historical,
        "_HistoricalFxAlignmentResolver",
    )
