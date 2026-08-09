"""Tests for deterministic text formatting of historical reconciliation evaluation summaries."""

from datetime import UTC, datetime

import pytest
from navlens import (
    AssetClass,
    HoldingPosition,
    MarketDate,
    ReturnPeriod,
)
from navlens.datasets import HoldingSnapshot
from navlens.reconciliation.historical import (
    HistoricalReconciliationDataset,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    build_historical_reconciliation_dataset,
    evaluate_historical_reconciliation_dataset,
    format_historical_reconciliation_evaluation,
)
from tests.historical_fx_reconciliation_fixtures import (
    make_fund_price_snap,
    make_security_price_snap,
)
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_fx_dataset,
    build_two_period_legacy_dataset,
    make_legacy_request,
    make_skipped_legacy_record,
)


def test_formats_empty_legacy_evaluation() -> None:
    ds = HistoricalReconciliationDataset(outcomes=())
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    report = format_historical_reconciliation_evaluation(evaluation)

    assert "Historical Reconciliation Evaluation" in report
    assert "Scope: None" in report
    assert "Total Period Count: 0" in report
    assert "Reconciliation Metrics: Unavailable" in report
    assert "WARNING" not in report


def test_formats_successful_legacy_evaluation() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    report = format_historical_reconciliation_evaluation(evaluation)

    assert "Scope Kind: Legacy" in report
    assert "Fund ID: TEST_FUND" in report
    assert "Holdings Source ID: src_h" in report
    assert "Security Price Source ID: src_p" in report
    assert "Fund Price Source ID: src_f" in report
    assert "FX Source ID" not in report

    assert "Total Period Count: 2" in report
    assert "Evaluated Period Count: 2" in report
    assert "Skipped Period Count: 0" in report

    assert "Sample Count: 2" in report
    assert "Mean Absolute Residual (Decimal):" in report
    assert "Mean Residual (Decimal):" in report
    assert "Root Mean Squared Residual (Decimal):" in report
    assert "Mean Return Coverage (Ratio):" in report
    assert "Full Return Coverage (Ratio):" in report


def test_formats_successful_fx_aware_evaluation() -> None:
    ds = build_two_period_fx_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    report = format_historical_reconciliation_evaluation(evaluation)

    assert "Scope Kind: FX-Aware" in report
    assert "FX Source ID: src_fx" in report


def test_formats_all_skipped_evaluation_with_warning() -> None:
    skip1 = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)
    skip2 = make_skipped_legacy_record(MissingFundPriceSkip(MarketDate(2026, 1, 3)), 2, 3)

    ds = HistoricalReconciliationDataset(outcomes=(skip1, skip2))
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    report = format_historical_reconciliation_evaluation(evaluation)

    assert "Total Period Count: 2" in report
    assert "Evaluated Period Count: 0" in report
    assert "Skipped Period Count: 2" in report
    assert "Missing Holdings Count: 1" in report
    assert "Missing Fund Price Count: 1" in report
    assert "Reconciliation Metrics: Unavailable" in report
    assert "WARNING: Skipped periods exist (2 of 2 periods skipped)." in report


def test_formats_mixed_outcomes_with_skipped_warning() -> None:
    full_ds = build_two_period_legacy_dataset()
    skip = make_skipped_legacy_record(MissingHoldingsSkip(), 3, 4)

    mixed_ds = HistoricalReconciliationDataset(outcomes=full_ds.outcomes + (skip,))
    evaluation = evaluate_historical_reconciliation_dataset(mixed_ds)
    report = format_historical_reconciliation_evaluation(evaluation)

    assert "Total Period Count: 3" in report
    assert "Evaluated Period Count: 2" in report
    assert "Skipped Period Count: 1" in report
    assert "WARNING: Skipped periods exist (1 of 3 periods skipped)." in report


def test_formats_incomplete_return_coverage_warning() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req = make_legacy_request(MarketDate(2026, 1, 2), tz, period)

    holdings = [
        HoldingSnapshot(
            "TEST_FUND",
            MarketDate(2026, 1, 1),
            tz,
            tz,
            "src_h",
            [HoldingPosition("INST_A", AssetClass("equity"), 0.5)],
        )
    ]
    prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz),
        make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, tz),
    ]

    ds = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    evaluation = evaluate_historical_reconciliation_dataset(ds)

    assert evaluation.metrics is not None
    assert evaluation.metrics.full_return_coverage_ratio < 1.0

    report = format_historical_reconciliation_evaluation(evaluation)
    assert "WARNING: Some evaluated periods do not have full return coverage." in report
    assert "must not be interpreted as pure prediction error or alpha." in report


def test_formatting_preserves_evaluation_instance_unmodified() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)

    metrics_id = id(evaluation.metrics)
    scope_id = id(evaluation.scope)
    total_count = evaluation.total_period_count
    evaluated_count = evaluation.evaluated_period_count
    skipped_count = evaluation.skipped_period_count
    missing_holdings = evaluation.missing_holdings_count
    missing_price = evaluation.missing_fund_price_count

    format_historical_reconciliation_evaluation(evaluation)

    assert id(evaluation.metrics) == metrics_id
    assert id(evaluation.scope) == scope_id
    assert evaluation.total_period_count == total_count
    assert evaluation.evaluated_period_count == evaluated_count
    assert evaluation.skipped_period_count == skipped_count
    assert evaluation.missing_holdings_count == missing_holdings
    assert evaluation.missing_fund_price_count == missing_price


def test_formatting_output_is_deterministic() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)

    report1 = format_historical_reconciliation_evaluation(evaluation)
    report2 = format_historical_reconciliation_evaluation(evaluation)

    assert report1 == report2
    assert "<HistoricalReconciliationEvaluation" not in report1
    assert "0x" not in report1


def test_format_raises_type_error_for_invalid_input() -> None:
    with pytest.raises(TypeError, match="evaluation must be a HistoricalReconciliationEvaluation"):
        format_historical_reconciliation_evaluation("not_an_evaluation")  # type: ignore[arg-type]
