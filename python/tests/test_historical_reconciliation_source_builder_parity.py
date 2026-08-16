"""Field-by-field parity tests comparing source-backed and snapshot-backed builders."""

from datetime import date

import pytest
from navlens import MarketDate
from navlens.reconciliation.historical import (
    HistoricalReconciliationDataset,
    HistoricalReconciliationRecord,
    MissingFundPriceSkip,
    SkippedReconciliationRecord,
    build_historical_reconciliation_dataset,
    build_historical_reconciliation_dataset_from_source,
)
from tests.historical_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_cash_position,
    make_equity_position,
    make_etf_position,
    make_fund_unit_price_snapshot,
    make_historical_request,
    make_holding_snapshot,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def assert_historical_dataset_parity(
    source_dataset: HistoricalReconciliationDataset,
    direct_dataset: HistoricalReconciliationDataset,
) -> None:
    """Perform field-by-field parity assertions without using generic == on PyO3 wrappers."""
    assert len(source_dataset.outcomes) == len(direct_dataset.outcomes)

    for idx, (source_outcome, direct_outcome) in enumerate(
        zip(source_dataset.outcomes, direct_dataset.outcomes, strict=True)
    ):
        assert type(source_outcome) is type(direct_outcome), f"Outcome type mismatch at index {idx}"
        assert source_outcome.request is direct_outcome.request, (
            f"Request identity mismatch at index {idx}"
        )

        if isinstance(source_outcome, HistoricalReconciliationRecord):
            assert isinstance(direct_outcome, HistoricalReconciliationRecord)
            assert source_outcome.published_fund_return == pytest.approx(
                direct_outcome.published_fund_return
            )
            assert source_outcome.observed_portfolio_contribution == pytest.approx(
                direct_outcome.observed_portfolio_contribution
            )
            assert source_outcome.return_coverage == pytest.approx(direct_outcome.return_coverage)
            assert source_outcome.reconciliation_residual == pytest.approx(
                direct_outcome.reconciliation_residual
            )

            assert (
                source_outcome.result.fund_price_source_id
                == direct_outcome.result.fund_price_source_id
            )
            assert source_outcome.result.start_snapshot is direct_outcome.result.start_snapshot
            assert source_outcome.result.end_snapshot is direct_outcome.result.end_snapshot
            assert (
                source_outcome.result.contribution.alignment_result.holdings_snapshot
                is direct_outcome.result.contribution.alignment_result.holdings_snapshot
            )

        elif isinstance(source_outcome, SkippedReconciliationRecord):
            assert isinstance(direct_outcome, SkippedReconciliationRecord)
            assert type(source_outcome.reason) is type(direct_outcome.reason), (
                f"Skip reason mismatch at index {idx}"
            )
            if isinstance(source_outcome.reason, MissingFundPriceSkip):
                assert isinstance(direct_outcome.reason, MissingFundPriceSkip)
                assert source_outcome.reason.required_date == direct_outcome.reason.required_date


def test_full_coverage_multi_period_parity() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)
    requests = [req1, req2]

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("GARAN", 0.6), make_etf_position("GLDTR", 0.4)),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("GARAN", 0.5), make_etf_position("GLDTR", 0.5)),
        ),
    ]

    garan_p1 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz1)
    garan_p2 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz1)
    garan_p3 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 3), 12.1, tz2)

    gldtr_p1 = make_security_price_snapshot("GLDTR", MarketDate(2026, 1, 1), 20.0, tz1)
    gldtr_p2 = make_security_price_snapshot("GLDTR", MarketDate(2026, 1, 2), 21.0, tz1)
    gldtr_p3 = make_security_price_snapshot("GLDTR", MarketDate(2026, 1, 3), 23.1, tz2)

    all_prices = [garan_p1, garan_p2, garan_p3, gldtr_p1, gldtr_p2, gldtr_p3]
    source = FakeRecordingSecurityPriceSource(
        data={
            "GARAN": (garan_p1, garan_p2, garan_p3),
            "GLDTR": (gldtr_p1, gldtr_p2, gldtr_p3),
        }
    )

    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 108.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 118.8, tz2),
    ]

    direct_dataset = build_historical_reconciliation_dataset(
        requests, holdings, all_prices, fund_prices
    )
    source_dataset = build_historical_reconciliation_dataset_from_source(
        requests,
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_dataset_parity(source_dataset, direct_dataset)


def test_partial_coverage_market_gap_parity() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (
                make_equity_position("GARAN", 0.5),
                make_equity_position("AKBNK", 0.3),
                make_cash_position("TRY_CASH", 0.2),
            ),
        )
    ]

    # AKBNK has missing end price (market gap)
    garan_p1 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 1), 10.0, tz)
    garan_p2 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 11.0, tz)
    akbnk_p1 = make_security_price_snapshot("AKBNK", MarketDate(2026, 1, 1), 20.0, tz)

    all_prices = [garan_p1, garan_p2, akbnk_p1]
    source = FakeRecordingSecurityPriceSource(
        data={
            "GARAN": (garan_p1, garan_p2),
            "AKBNK": (akbnk_p1,),
        }
    )

    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 105.0, tz),
    ]

    direct_dataset = build_historical_reconciliation_dataset(
        [req], holdings, all_prices, fund_prices
    )
    source_dataset = build_historical_reconciliation_dataset_from_source(
        [req],
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_dataset_parity(source_dataset, direct_dataset)


def test_mixed_skips_parity() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)
    tz3 = make_utc_timestamp(2026, 1, 4)

    req1 = make_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)
    req3 = make_historical_request(MarketDate(2026, 1, 3), MarketDate(2026, 1, 4), tz3)
    requests = [req1, req2, req3]

    # req1 has missing holdings, req2 is successful, req3 has missing end fund price
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("GARAN", 1.0),),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 3),
            tz3,
            (make_equity_position("GARAN", 1.0),),
        ),
    ]

    garan_p2 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 2), 10.0, tz2)
    garan_p3 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 3), 11.0, tz2)
    garan_p4 = make_security_price_snapshot("GARAN", MarketDate(2026, 1, 4), 12.0, tz3)

    all_prices = [garan_p2, garan_p3, garan_p4]
    source = FakeRecordingSecurityPriceSource(data={"GARAN": (garan_p2, garan_p3, garan_p4)})

    # Missing fund price for 2026-01-04
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 100.0, tz2),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 110.0, tz2),
    ]

    direct_dataset = build_historical_reconciliation_dataset(
        requests, holdings, all_prices, fund_prices
    )
    source_dataset = build_historical_reconciliation_dataset_from_source(
        requests,
        holdings,
        source,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_dataset_parity(source_dataset, direct_dataset)
