"""Core integration tests for source-backed historical reconciliation dataset builder."""

from collections.abc import Iterator
from datetime import date

import pytest
from navlens import MarketDate
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import FundUnitPriceSnapshot, HoldingSnapshot, SecurityPriceQuery
from navlens.reconciliation.historical import (
    HistoricalReconciliationRecord,
    HistoricalReconciliationRequest,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
    build_historical_reconciliation_dataset,
    build_historical_reconciliation_dataset_from_source,
)
from tests.historical_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_alignment_policy,
    make_cash_position,
    make_deposit_position,
    make_derivative_position,
    make_equity_position,
    make_etf_position,
    make_fund_unit_price_snapshot,
    make_historical_request,
    make_holding_snapshot,
    make_repo_position,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def test_single_period_successful_reconciliation() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("GARAN", 0.6), make_etf_position("GLDTR", 0.4)),
        )
    ]
    prices = {
        "GARAN": (
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz),
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz),
        ),
        "GLDTR": (
            make_security_price_snapshot("GLDTR", MarketDate(2026, 1, 1), 20.0, tz),
            make_security_price_snapshot("GLDTR", MarketDate(2026, 1, 2), 22.0, tz),
        ),
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalReconciliationRecord)
    assert rec.request is req
    assert rec.result.start_snapshot is fund_prices[0]
    assert rec.result.end_snapshot is fund_prices[1]
    assert rec.result.fund_price_source_id == "src_f"
    assert rec.result.contribution.alignment_result.holdings_snapshot is holdings[0]
    assert rec.return_coverage == pytest.approx(1.0)
    assert rec.observed_portfolio_contribution == pytest.approx(0.1)
    assert rec.published_fund_return == pytest.approx(0.1)
    assert rec.reconciliation_residual == pytest.approx(0.0)


def test_multiple_chronological_periods_and_result_ordering() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("GARAN", 1.0),),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("GARAN", 1.0),),
        ),
    ]
    prices = {
        "GARAN": (
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz1),
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz1),
            make_security_price_snapshot("GARAN", MarketDate(2026, 1, 3), 12.1, tz2),
        ),
    }
    source = FakeRecordingSecurityPriceSource(data=prices)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 121.0, tz2),
    ]

    dataset = build_historical_reconciliation_dataset_from_source(
        [req1, req2],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 2
    rec1, rec2 = dataset.outcomes

    assert isinstance(rec1, HistoricalReconciliationRecord)
    assert isinstance(rec2, HistoricalReconciliationRecord)
    assert rec1.request is req1
    assert rec2.request is req2
    assert rec1.result.start_snapshot is fund_prices[0]
    assert rec1.result.end_snapshot is fund_prices[1]
    assert rec2.result.start_snapshot is fund_prices[1]
    assert rec2.result.end_snapshot is fund_prices[2]
    assert rec1.result.contribution.alignment_result.holdings_snapshot is holdings[0]
    assert rec2.result.contribution.alignment_result.holdings_snapshot is holdings[1]
    assert rec1.return_coverage == pytest.approx(1.0)
    assert rec2.return_coverage == pytest.approx(1.0)
    assert rec1.observed_portfolio_contribution == pytest.approx(0.1)
    assert rec2.observed_portfolio_contribution == pytest.approx(0.1)


def test_exact_query_date_bounds_and_instrument_fields() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("GARAN", 0.5), make_etf_position("GLDTR", 0.5)),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("THYAO", 1.0),),
        ),
    ]
    source = FakeRecordingSecurityPriceSource()
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 120.0, tz2),
    ]

    build_historical_reconciliation_dataset_from_source(
        [req1, req2],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2025, 12, 25),
    )

    assert len(source.queries) == 3
    assert source.queries[0] == SecurityPriceQuery(
        instrument_id="GARAN",
        start_date=date(2025, 12, 25),
        end_date=date(2026, 1, 2),
    )
    assert source.queries[1] == SecurityPriceQuery(
        instrument_id="GLDTR",
        start_date=date(2025, 12, 25),
        end_date=date(2026, 1, 2),
    )
    assert source.queries[2] == SecurityPriceQuery(
        instrument_id="THYAO",
        start_date=date(2025, 12, 25),
        end_date=date(2026, 1, 3),
    )


def test_generator_inputs_consumed_once() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holding = make_holding_snapshot(
        MarketDate(2026, 1, 1),
        tz,
        (make_equity_position("GARAN", 1.0),),
    )
    fund_p1 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)
    fund_p2 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz)

    source = FakeRecordingSecurityPriceSource(
        data={
            "GARAN": (
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz),
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz),
            )
        }
    )

    def req_gen() -> Iterator[HistoricalReconciliationRequest]:
        yield req

    def holdings_gen() -> Iterator[HoldingSnapshot]:
        yield holding

    def fund_gen() -> Iterator[FundUnitPriceSnapshot]:
        yield fund_p1
        yield fund_p2

    dataset = build_historical_reconciliation_dataset_from_source(
        req_gen(),
        holdings_gen(),
        source,
        fund_gen(),
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    assert isinstance(dataset.outcomes[0], HistoricalReconciliationRecord)


def test_source_builder_materialization_order() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holding = make_holding_snapshot(
        MarketDate(2026, 1, 1),
        tz,
        (make_equity_position("GARAN", 1.0),),
    )
    fund_p1 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)
    fund_p2 = make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz)

    source = FakeRecordingSecurityPriceSource(
        data={
            "GARAN": (
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz),
                make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz),
            )
        }
    )

    consumption_order: list[str] = []

    def req_iter() -> Iterator[HistoricalReconciliationRequest]:
        consumption_order.append("requests")
        yield req

    def holdings_iter() -> Iterator[HoldingSnapshot]:
        consumption_order.append("holdings")
        yield holding

    def fund_iter() -> Iterator[FundUnitPriceSnapshot]:
        consumption_order.append("fund_prices")
        yield fund_p1
        yield fund_p2

    build_historical_reconciliation_dataset_from_source(
        req_iter(),
        holdings_iter(),
        source,
        fund_iter(),
        price_history_start_date=date(2026, 1, 1),
    )

    assert consumption_order == ["requests", "holdings", "fund_prices"]


def test_minimum_observations_price_history_start_date_regression() -> None:
    """Verify price_history_start_date provides required observations before period_start_date."""
    tz = make_utc_timestamp(2026, 1, 3)
    policy_3_obs = make_alignment_policy(
        MarketDate(2026, 1, 3),
        minimum_observations=3,
    )
    align_req = PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=tz,
        policy=policy_3_obs,
    )
    req = HistoricalReconciliationRequest(
        alignment_request=align_req,
        period=make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz).period,
        fund_price_source_id="src_f",
    )

    holding = make_holding_snapshot(
        MarketDate(2026, 1, 2),
        tz,
        (make_equity_position("GARAN", 1.0),),
    )

    # 3 observations: 2026-01-01, 2026-01-02, 2026-01-03
    p1 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz)
    p2 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz)
    p3 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 3), 12.1, tz)

    source = FakeRecordingSecurityPriceSource(data={"GARAN": (p1, p2, p3)})
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 121.0, tz),
    ]

    direct_dataset = build_historical_reconciliation_dataset(
        [req], [holding], [p1, p2, p3], fund_prices
    )
    source_dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        [holding],
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 1
    assert source.queries[0].start_date == date(2026, 1, 1)
    assert source.queries[0].start_date != date(2026, 1, 2)
    assert source.queries[0].end_date == date(2026, 1, 3)

    direct_rec = direct_dataset.outcomes[0]
    source_rec = source_dataset.outcomes[0]
    assert isinstance(direct_rec, HistoricalReconciliationRecord)
    assert isinstance(source_rec, HistoricalReconciliationRecord)
    assert source_rec.return_coverage == pytest.approx(1.0)
    assert direct_rec.return_coverage == pytest.approx(1.0)
    assert source_rec.observed_portfolio_contribution == pytest.approx(
        direct_rec.observed_portfolio_contribution
    )
    assert source_rec.published_fund_return == pytest.approx(direct_rec.published_fund_return)
    assert source_rec.reconciliation_residual == pytest.approx(direct_rec.reconciliation_residual)


def test_unsupported_asset_classes_produce_zero_source_queries_and_typed_gaps() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

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

    dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 0
    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalReconciliationRecord)
    assert rec.return_coverage == pytest.approx(0.0)
    assert rec.observed_portfolio_contribution == pytest.approx(0.0)
    assert rec.published_fund_return == pytest.approx(0.1)
    assert rec.reconciliation_residual == pytest.approx(0.1)
    report = rec.result.contribution.alignment_result.report
    assert len(report.uncovered_listed) == 4
    for uncovered in report.uncovered_listed:
        assert uncovered.reason.kind == "unsupported_asset_class"


def test_missing_holdings_yields_typed_skip_with_zero_source_queries() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    source = FakeRecordingSecurityPriceSource()
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        [],
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(source.queries) == 0
    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingHoldingsSkip)
    assert rec.request is req


def test_missing_start_fund_price_yields_typed_skip() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("GARAN", 1.0),),
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
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz)]

    dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 1)


def test_missing_end_fund_price_yields_typed_skip() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("GARAN", 1.0),),
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
    fund_prices = [make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz)]

    dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 2)


def test_public_export_boundary() -> None:
    import navlens
    import navlens.reconciliation
    import navlens.reconciliation.historical

    assert hasattr(
        navlens.reconciliation.historical,
        "build_historical_reconciliation_dataset_from_source",
    )
    assert not hasattr(navlens, "build_historical_reconciliation_dataset_from_source")
    assert not hasattr(
        navlens.reconciliation,
        "build_historical_reconciliation_dataset_from_source",
    )
    assert not hasattr(navlens.reconciliation.historical, "_execute_historical_reconciliation")
    assert not hasattr(navlens.reconciliation.historical, "_HistoricalAlignmentResolver")
