"""Integration tests for historical FX-aware fund return reconciliation dataset builder."""

from datetime import UTC, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    ReturnPeriod,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceSnapshot,
)
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRecord,
    HistoricalFxReconciliationRequest,
    HistoricalReconciliationRecord,
    HistoricalReconciliationRequest,
    build_historical_fx_reconciliation_dataset,
    build_historical_reconciliation_dataset,
)
from tests.historical_fx_reconciliation_fixtures import (
    make_fund_price_snap,
    make_fx_rate_snap,
    make_fx_request,
    make_holding_snap,
    make_security_price_snap,
)


def test_builds_consecutive_fx_records_successfully() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    tz2 = datetime(2026, 1, 3, 10, tzinfo=UTC)

    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    p2 = ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3))

    req1 = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)
    req2 = make_fx_request(MarketDate(2026, 1, 3), tz2, p2)

    holdings = [
        make_holding_snap(MarketDate(2026, 1, 1), tz1),
        make_holding_snap(MarketDate(2026, 1, 2), tz2),
    ]
    security_prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
        make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
        make_security_price_snap(MarketDate(2026, 1, 3), 110.0, tz2),
    ]
    fx_rates = [
        make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, tz1),
        make_fx_rate_snap(MarketDate(2026, 1, 2), 31.0, tz1),
        make_fx_rate_snap(MarketDate(2026, 1, 3), 32.0, tz2),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.845, tz1),
        make_fund_price_snap(MarketDate(2026, 1, 3), 11.71, tz2),
    ]

    dataset = build_historical_fx_reconciliation_dataset(
        [req1, req2],
        holdings,
        security_prices,
        fx_rates,
        fund_prices,
    )

    assert len(dataset.outcomes) == 2
    rec1 = dataset.outcomes[0]
    rec2 = dataset.outcomes[1]

    assert isinstance(rec1, HistoricalFxReconciliationRecord)
    assert isinstance(rec2, HistoricalFxReconciliationRecord)
    assert rec1.request is req1
    assert rec2.request is req2
    assert rec1.result.contribution.request.alignment_result.request is req1.alignment_request
    assert rec1.result.contribution.request.target_period is req1.period
    assert rec1.result.start_snapshot is fund_prices[0]
    assert rec1.result.end_snapshot is fund_prices[1]
    assert rec1.published_fund_return == pytest.approx(0.0845)
    assert isinstance(rec1.return_coverage, float)

    repeated = build_historical_fx_reconciliation_dataset(
        [req1, req2],
        holdings,
        security_prices,
        fx_rates,
        fund_prices,
    )
    expected_projection = [
        (
            record.request.period,
            record.published_fund_return,
            record.return_coverage,
            record.observed_portfolio_contribution,
            record.reconciliation_residual,
        )
        for record in (rec1, rec2)
    ]
    repeated_records = repeated.outcomes
    assert all(isinstance(record, HistoricalFxReconciliationRecord) for record in repeated_records)
    actual_projection = [
        (
            record.request.period,
            record.published_fund_return,
            record.return_coverage,
            record.observed_portfolio_contribution,
            record.reconciliation_residual,
        )
        for record in repeated_records
        if isinstance(record, HistoricalFxReconciliationRecord)
    ]
    assert actual_projection == expected_projection


def test_consumes_generator_inputs_once() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req1 = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)

    dataset = build_historical_fx_reconciliation_dataset(
        (r for r in [req1]),
        (h for h in [make_holding_snap(MarketDate(2026, 1, 1), tz1)]),
        (
            sp
            for sp in [
                make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
                make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
            ]
        ),
        (
            fx
            for fx in [
                make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, tz1),
                make_fx_rate_snap(MarketDate(2026, 1, 2), 31.0, tz1),
            ]
        ),
        (
            fp
            for fp in [
                make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
                make_fund_price_snap(MarketDate(2026, 1, 2), 10.845, tz1),
            ]
        ),
    )
    assert len(dataset.outcomes) == 1
    assert isinstance(dataset.outcomes[0], HistoricalFxReconciliationRecord)


def test_missing_fx_produces_successful_record_with_gaps() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req1 = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)

    holdings = [make_holding_snap(MarketDate(2026, 1, 1), tz1)]
    security_prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
        make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
    ]
    # No FX rate provided
    fx_rates: list = []
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, tz1),
    ]

    dataset = build_historical_fx_reconciliation_dataset(
        [req1],
        holdings,
        security_prices,
        fx_rates,
        fund_prices,
    )
    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalFxReconciliationRecord)
    assert len(rec.result.contribution.contribution_result.return_gaps) > 0


def test_stale_fx_produces_successful_record_with_reduced_coverage() -> None:
    prediction_time = datetime(2026, 1, 10, 10, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 9), MarketDate(2026, 1, 10))
    request = make_fx_request(MarketDate(2026, 1, 10), prediction_time, period)
    stale_date = MarketDate(2025, 12, 20)

    dataset = build_historical_fx_reconciliation_dataset(
        [request],
        [make_holding_snap(MarketDate(2026, 1, 9), prediction_time)],
        [
            make_security_price_snap(MarketDate(2026, 1, 9), 100.0, prediction_time),
            make_security_price_snap(MarketDate(2026, 1, 10), 105.0, prediction_time),
        ],
        [make_fx_rate_snap(stale_date, 30.0, prediction_time)],
        [
            make_fund_price_snap(MarketDate(2026, 1, 9), 10.0, prediction_time),
            make_fund_price_snap(MarketDate(2026, 1, 10), 10.5, prediction_time),
        ],
    )

    record = dataset.outcomes[0]
    assert isinstance(record, HistoricalFxReconciliationRecord)
    assert record.return_coverage == 0.0
    assert record.result.contribution.contribution_result.return_gaps[0].reason.kind == (
        "stale_fx_start_observation"
    )


def test_zero_fx_return_parity_with_legacy_builder() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))

    # The legacy USD-base path and the TRY-base FX path must agree when USD/TRY is flat.
    non_fx_align_req = PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=tz1,
        policy=AlignmentPolicy(
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
            MarketDate(2026, 1, 2),
            minimum_observations=2,
            max_staleness_calendar_days=5,
        ),
    )
    legacy_req = HistoricalReconciliationRequest(
        alignment_request=non_fx_align_req,
        period=p1,
        fund_price_source_id="src_f",
    )

    fx_req = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)
    holdings = [make_holding_snap(MarketDate(2026, 1, 1), tz1)]
    prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
        make_security_price_snap(MarketDate(2026, 1, 2), 110.0, tz1),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_price_snap(MarketDate(2026, 1, 2), 11.0, tz1),
    ]

    legacy_ds = build_historical_reconciliation_dataset(
        [legacy_req],
        holdings,
        prices,
        fund_prices,
    )
    fx_ds = build_historical_fx_reconciliation_dataset(
        [fx_req],
        holdings,
        prices,
        [
            make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, tz1),
            make_fx_rate_snap(MarketDate(2026, 1, 2), 30.0, tz1),
        ],
        fund_prices,
    )

    legacy_rec = legacy_ds.outcomes[0]
    fx_rec = fx_ds.outcomes[0]

    assert isinstance(legacy_rec, HistoricalReconciliationRecord)
    assert isinstance(fx_rec, HistoricalFxReconciliationRecord)
    assert legacy_rec.published_fund_return == fx_rec.published_fund_return
    assert legacy_rec.observed_portfolio_contribution == fx_rec.observed_portfolio_contribution
    assert legacy_rec.reconciliation_residual == fx_rec.reconciliation_residual


def test_legacy_fx_builder_materialization_order() -> None:
    from collections.abc import Iterator

    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)
    holding = make_holding_snap(MarketDate(2026, 1, 1), tz1)
    price = make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1)
    fx = make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, tz1)
    fund_p1 = make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1)
    fund_p2 = make_fund_price_snap(MarketDate(2026, 1, 2), 11.0, tz1)

    consumption_order: list[str] = []

    def req_iter() -> Iterator[HistoricalFxReconciliationRequest]:
        consumption_order.append("requests")
        yield req

    def holdings_iter() -> Iterator[HoldingSnapshot]:
        consumption_order.append("holdings")
        yield holding

    def prices_iter() -> Iterator[SecurityPriceSnapshot]:
        consumption_order.append("security_prices")
        yield price

    def fx_iter() -> Iterator[FxRateSnapshot]:
        consumption_order.append("fx_rates")
        yield fx

    def fund_iter() -> Iterator[FundUnitPriceSnapshot]:
        consumption_order.append("fund_prices")
        yield fund_p1
        yield fund_p2

    build_historical_fx_reconciliation_dataset(
        req_iter(),
        holdings_iter(),
        prices_iter(),
        fx_iter(),
        fund_iter(),
    )

    assert consumption_order == [
        "requests",
        "holdings",
        "security_prices",
        "fx_rates",
        "fund_prices",
    ]
