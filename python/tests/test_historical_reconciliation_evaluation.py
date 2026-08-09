"""Behavior tests for historical reconciliation dataset evaluation."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from navlens import (
    AssetClass,
    HoldingPosition,
    MarketDate,
    ReconciliationMetrics,
    ReturnPeriod,
    evaluate_reconciliation_metrics,
)
from navlens.datasets import HoldingSnapshot
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationDataset,
    HistoricalReconciliationDataset,
    HistoricalReconciliationEvaluation,
    HistoricalReconciliationSkipReason,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
    UnknownOutcomeError,
    UnknownSkipReasonError,
    UnsupportedHistoricalReconciliationDatasetError,
    build_historical_fx_reconciliation_dataset,
    build_historical_reconciliation_dataset,
    evaluate_historical_reconciliation_dataset,
)
from tests.historical_fx_reconciliation_fixtures import (
    make_fund_price_snap,
    make_fx_rate_snap,
    make_fx_request,
    make_security_price_snap,
)
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_fx_dataset,
    build_two_period_legacy_dataset,
    make_legacy_request,
    make_skipped_legacy_record,
    successful_results,
)


@pytest.mark.parametrize(
    "dataset",
    [
        HistoricalReconciliationDataset(outcomes=()),
        HistoricalFxReconciliationDataset(outcomes=()),
    ],
)
def test_evaluates_empty_dataset(
    dataset: HistoricalReconciliationDataset | HistoricalFxReconciliationDataset,
) -> None:
    evaluation = evaluate_historical_reconciliation_dataset(dataset)

    assert evaluation == HistoricalReconciliationEvaluation(None, 0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "dataset_builder",
    [build_two_period_legacy_dataset, build_two_period_fx_dataset],
)
def test_delegates_successful_results_to_native_metrics(
    dataset_builder: Callable[
        [], HistoricalReconciliationDataset | HistoricalFxReconciliationDataset
    ],
) -> None:
    dataset = dataset_builder()
    evaluation = evaluate_historical_reconciliation_dataset(dataset)
    direct = evaluate_reconciliation_metrics(successful_results(dataset))

    assert isinstance(evaluation.metrics, ReconciliationMetrics)
    assert evaluation.total_period_count == 2
    assert evaluation.evaluated_period_count == 2
    assert evaluation.skipped_period_count == 0
    _assert_metrics_equal(evaluation.metrics, direct)


def test_counts_mixed_successful_and_skipped_outcomes() -> None:
    successful_dataset = build_two_period_legacy_dataset()
    skipped_holdings = make_skipped_legacy_record(MissingHoldingsSkip(), 3, 4)
    skipped_price = make_skipped_legacy_record(
        MissingFundPriceSkip(MarketDate(2026, 1, 5)),
        4,
        5,
    )
    outcomes = successful_dataset.outcomes + (skipped_holdings, skipped_price)
    dataset = HistoricalReconciliationDataset(outcomes=outcomes)

    evaluation = evaluate_historical_reconciliation_dataset(dataset)

    assert evaluation.total_period_count == 4
    assert evaluation.evaluated_period_count == 2
    assert evaluation.skipped_period_count == 2
    assert evaluation.missing_holdings_count == 1
    assert evaluation.missing_fund_price_count == 1


def test_evaluates_all_skipped_dataset_without_native_metrics() -> None:
    outcomes = (
        make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2),
        make_skipped_legacy_record(
            MissingFundPriceSkip(MarketDate(2026, 1, 3)),
            2,
            3,
        ),
    )

    evaluation = evaluate_historical_reconciliation_dataset(
        HistoricalReconciliationDataset(outcomes=outcomes)
    )

    assert evaluation.metrics is None
    assert evaluation.total_period_count == 2
    assert evaluation.evaluated_period_count == 0
    assert evaluation.skipped_period_count == 2
    assert evaluation.missing_holdings_count == 1
    assert evaluation.missing_fund_price_count == 1


@pytest.mark.parametrize(
    ("reason", "expected_holdings", "expected_price"),
    [
        (MissingHoldingsSkip(), 1, 0),
        (MissingFundPriceSkip(MarketDate(2026, 1, 2)), 0, 1),
    ],
)
def test_counts_each_typed_skip_reason(
    reason: HistoricalReconciliationSkipReason,
    expected_holdings: int,
    expected_price: int,
) -> None:
    record = make_skipped_legacy_record(reason, 1, 2)
    dataset = HistoricalReconciliationDataset(outcomes=(record,))

    evaluation = evaluate_historical_reconciliation_dataset(dataset)

    assert evaluation.missing_holdings_count == expected_holdings
    assert evaluation.missing_fund_price_count == expected_price


def test_legacy_and_fx_results_have_metric_parity() -> None:
    timestamp = datetime(2026, 1, 2, 10, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    legacy_request = make_legacy_request(MarketDate(2026, 1, 2), timestamp, period)
    fx_request = make_fx_request(MarketDate(2026, 1, 2), timestamp, period)
    holdings = [
        HoldingSnapshot(
            "TEST_FUND",
            MarketDate(2026, 1, 1),
            timestamp,
            timestamp,
            "src_h",
            [HoldingPosition("INST_A", AssetClass("equity"), 1.0)],
        )
    ]
    prices = [
        make_security_price_snap(MarketDate(2026, 1, 1), 100.0, timestamp),
        make_security_price_snap(MarketDate(2026, 1, 2), 110.0, timestamp),
    ]
    fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, timestamp),
        make_fund_price_snap(MarketDate(2026, 1, 2), 11.0, timestamp),
    ]
    legacy_dataset = build_historical_reconciliation_dataset(
        [legacy_request], holdings, prices, fund_prices
    )
    fx_dataset = build_historical_fx_reconciliation_dataset(
        [fx_request],
        holdings,
        prices,
        [
            make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, timestamp),
            make_fx_rate_snap(MarketDate(2026, 1, 2), 30.0, timestamp),
        ],
        fund_prices,
    )

    legacy_evaluation = evaluate_historical_reconciliation_dataset(legacy_dataset)
    fx_evaluation = evaluate_historical_reconciliation_dataset(fx_dataset)

    assert legacy_evaluation.metrics is not None
    assert fx_evaluation.metrics is not None
    assert legacy_evaluation.total_period_count == fx_evaluation.total_period_count
    assert legacy_evaluation.evaluated_period_count == fx_evaluation.evaluated_period_count
    assert legacy_evaluation.skipped_period_count == fx_evaluation.skipped_period_count
    _assert_metrics_equal(legacy_evaluation.metrics, fx_evaluation.metrics)


def test_rejects_unknown_dataset_outcome_and_skip_reason_types() -> None:
    class UnknownOutcome:
        pass

    class UnknownSkipReason:
        pass

    with pytest.raises(UnsupportedHistoricalReconciliationDatasetError, match="dict"):
        evaluate_historical_reconciliation_dataset({})  # type: ignore[arg-type]

    unknown_dataset = HistoricalReconciliationDataset(
        outcomes=(UnknownOutcome(),)  # type: ignore[arg-type]
    )
    with pytest.raises(UnknownOutcomeError, match="UnknownOutcome"):
        evaluate_historical_reconciliation_dataset(unknown_dataset)

    valid_skipped = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)
    unknown_skipped = SkippedReconciliationRecord(
        request=valid_skipped.request,
        reason=UnknownSkipReason(),  # type: ignore[arg-type]
    )
    with pytest.raises(UnknownSkipReasonError, match="UnknownSkipReason"):
        evaluate_historical_reconciliation_dataset(
            HistoricalReconciliationDataset(outcomes=(unknown_skipped,))
        )


def test_preserves_input_dataset_outcome_identity_and_order() -> None:
    successful_dataset = build_two_period_legacy_dataset()
    skipped = make_skipped_legacy_record(MissingHoldingsSkip(), 3, 4)
    original_outcomes = successful_dataset.outcomes + (skipped,)
    dataset = HistoricalReconciliationDataset(outcomes=original_outcomes)

    evaluate_historical_reconciliation_dataset(dataset)

    assert len(dataset.outcomes) == len(original_outcomes)
    for original, current in zip(original_outcomes, dataset.outcomes, strict=True):
        assert original is current


def _assert_metrics_equal(
    actual: ReconciliationMetrics,
    expected: ReconciliationMetrics,
) -> None:
    assert actual.sample_count == expected.sample_count
    assert actual.mean_absolute_residual == pytest.approx(expected.mean_absolute_residual)
    assert actual.mean_residual == pytest.approx(expected.mean_residual)
    assert actual.root_mean_squared_residual == pytest.approx(expected.root_mean_squared_residual)
    assert actual.mean_return_coverage == pytest.approx(expected.mean_return_coverage)
    assert actual.full_return_coverage_ratio == pytest.approx(expected.full_return_coverage_ratio)
