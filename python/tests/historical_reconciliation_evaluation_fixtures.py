"""Focused builders for historical reconciliation evaluation tests."""

from datetime import UTC, datetime

from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    FundReturnReconciliationResult,
    HoldingPosition,
    MarketDate,
    PriceAdjustment,
    ReturnPeriod,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import HoldingSnapshot
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationDataset,
    HistoricalFxReconciliationRecord,
    HistoricalReconciliationDataset,
    HistoricalReconciliationRecord,
    HistoricalReconciliationRequest,
    HistoricalReconciliationSkipReason,
    SkippedReconciliationRecord,
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


def make_legacy_request(
    pricing_date: MarketDate,
    timestamp: datetime,
    period: ReturnPeriod,
) -> HistoricalReconciliationRequest:
    alignment_request = PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=timestamp,
        policy=AlignmentPolicy(
            CurrencyCode("TRY"),
            PriceAdjustment("unadjusted"),
            pricing_date,
            minimum_observations=2,
            max_staleness_calendar_days=5,
        ),
    )
    return HistoricalReconciliationRequest(
        alignment_request=alignment_request,
        period=period,
        fund_price_source_id="src_f",
    )


def build_two_period_legacy_dataset() -> HistoricalReconciliationDataset:
    timestamp_one = datetime(2026, 1, 2, 10, tzinfo=UTC)
    timestamp_two = datetime(2026, 1, 3, 10, tzinfo=UTC)
    period_one = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    period_two = ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3))
    requests = [
        make_legacy_request(MarketDate(2026, 1, 2), timestamp_one, period_one),
        make_legacy_request(MarketDate(2026, 1, 3), timestamp_two, period_two),
    ]
    holdings = [
        HoldingSnapshot(
            "TEST_FUND",
            MarketDate(2026, 1, 1),
            timestamp_one,
            timestamp_one,
            "src_h",
            [HoldingPosition("INST_A", AssetClass("equity"), 1.0)],
        ),
        HoldingSnapshot(
            "TEST_FUND",
            MarketDate(2026, 1, 2),
            timestamp_two,
            timestamp_two,
            "src_h",
            [HoldingPosition("INST_A", AssetClass("equity"), 1.0)],
        ),
    ]
    prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, timestamp_one),
        make_security_price_snap(MarketDate(2026, 1, 2), 105.0, timestamp_one),
        make_security_price_snap(MarketDate(2026, 1, 3), 110.0, timestamp_two),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, timestamp_one),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, timestamp_one),
        make_fund_price_snap(MarketDate(2026, 1, 3), 11.0, timestamp_two),
    ]
    return build_historical_reconciliation_dataset(requests, holdings, prices, fund_prices)


def build_two_period_fx_dataset() -> HistoricalFxReconciliationDataset:
    timestamp_one = datetime(2026, 1, 2, 10, tzinfo=UTC)
    timestamp_two = datetime(2026, 1, 3, 10, tzinfo=UTC)
    period_one = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    period_two = ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3))
    requests = [
        make_fx_request(MarketDate(2026, 1, 2), timestamp_one, period_one),
        make_fx_request(MarketDate(2026, 1, 3), timestamp_two, period_two),
    ]
    holdings = [
        make_holding_snap(MarketDate(2026, 1, 1), timestamp_one),
        make_holding_snap(MarketDate(2026, 1, 2), timestamp_two),
    ]
    prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, timestamp_one),
        make_security_price_snap(MarketDate(2026, 1, 2), 105.0, timestamp_one),
        make_security_price_snap(MarketDate(2026, 1, 3), 110.0, timestamp_two),
    ]
    fx_rates = [
        make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, timestamp_one),
        make_fx_rate_snap(MarketDate(2026, 1, 2), 31.0, timestamp_one),
        make_fx_rate_snap(MarketDate(2026, 1, 3), 32.0, timestamp_two),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, timestamp_one),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.845, timestamp_one),
        make_fund_price_snap(MarketDate(2026, 1, 3), 11.71, timestamp_two),
    ]
    return build_historical_fx_reconciliation_dataset(
        requests,
        holdings,
        prices,
        fx_rates,
        fund_prices,
    )


def make_skipped_legacy_record(
    reason: HistoricalReconciliationSkipReason,
    start_day: int,
    end_day: int,
) -> SkippedReconciliationRecord:
    timestamp = datetime(2026, 1, end_day, 10, tzinfo=UTC)
    period = ReturnPeriod(
        MarketDate(2026, 1, start_day),
        MarketDate(2026, 1, end_day),
    )
    request = make_legacy_request(period.period_end_date, timestamp, period)
    return SkippedReconciliationRecord(request=request, reason=reason)


def successful_results(
    dataset: HistoricalReconciliationDataset | HistoricalFxReconciliationDataset,
) -> list[FundReturnReconciliationResult]:
    results: list[FundReturnReconciliationResult] = []
    for outcome in dataset.outcomes:
        assert isinstance(
            outcome,
            (HistoricalReconciliationRecord, HistoricalFxReconciliationRecord),
        )
        results.append(outcome.result.reconciliation_result)
    return results
