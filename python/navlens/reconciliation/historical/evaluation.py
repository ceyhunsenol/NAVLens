"""Evaluation orchestrator for historical reconciliation datasets."""

from collections.abc import Iterable
from dataclasses import dataclass

from navlens import (
    FundReturnReconciliationResult,
    ReconciliationMetrics,
    evaluate_reconciliation_metrics,
)

from .dataset import HistoricalReconciliationDataset
from .errors import (
    InvalidHistoricalReconciliationEvaluationError,
    UnknownOutcomeError,
    UnknownSkipReasonError,
    UnsupportedHistoricalReconciliationDatasetError,
)
from .fx_dataset import HistoricalFxReconciliationDataset
from .fx_outcome import (
    HistoricalFxReconciliationRecord,
    SkippedFxReconciliationRecord,
)
from .outcome import (
    HistoricalReconciliationRecord,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
)


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationEvaluation:
    """Evaluation result summary for a historical reconciliation dataset."""

    metrics: ReconciliationMetrics | None
    total_period_count: int
    evaluated_period_count: int
    skipped_period_count: int
    missing_holdings_count: int
    missing_fund_price_count: int

    def __post_init__(self) -> None:
        """Validate result contract invariants."""
        for name, value in (
            ("total_period_count", self.total_period_count),
            ("evaluated_period_count", self.evaluated_period_count),
            ("skipped_period_count", self.skipped_period_count),
            ("missing_holdings_count", self.missing_holdings_count),
            ("missing_fund_price_count", self.missing_fund_price_count),
        ):
            _validate_count(name, value)

        _validate_count_relationships(self)
        _validate_metrics_relationship(self)


def _validate_count(name: str, value: object) -> None:
    if type(value) is not int:
        raise InvalidHistoricalReconciliationEvaluationError(
            f"{name} must be a non-bool integer, got {type(value).__name__}"
        )
    if value < 0:
        raise InvalidHistoricalReconciliationEvaluationError(
            f"{name} must be non-negative, got {value}"
        )


def _validate_count_relationships(result: HistoricalReconciliationEvaluation) -> None:
    if result.evaluated_period_count + result.skipped_period_count != result.total_period_count:
        raise InvalidHistoricalReconciliationEvaluationError(
            f"evaluated_period_count ({result.evaluated_period_count}) + "
            f"skipped_period_count ({result.skipped_period_count}) must equal "
            f"total_period_count ({result.total_period_count})"
        )

    if (
        result.missing_holdings_count + result.missing_fund_price_count
        != result.skipped_period_count
    ):
        raise InvalidHistoricalReconciliationEvaluationError(
            f"missing_holdings_count ({result.missing_holdings_count}) + "
            f"missing_fund_price_count ({result.missing_fund_price_count}) must equal "
            f"skipped_period_count ({result.skipped_period_count})"
        )


def _validate_metrics_relationship(result: HistoricalReconciliationEvaluation) -> None:
    if result.evaluated_period_count == 0:
        if result.metrics is not None:
            raise InvalidHistoricalReconciliationEvaluationError(
                "metrics must be None when evaluated_period_count is 0"
            )
        return

    if result.metrics is None:
        raise InvalidHistoricalReconciliationEvaluationError(
            "metrics must be non-None when evaluated_period_count > 0"
        )
    if not isinstance(result.metrics, ReconciliationMetrics):
        raise InvalidHistoricalReconciliationEvaluationError(
            f"metrics must be ReconciliationMetrics, got {type(result.metrics).__name__}"
        )
    if result.metrics.sample_count != result.evaluated_period_count:
        raise InvalidHistoricalReconciliationEvaluationError(
            f"metrics.sample_count ({result.metrics.sample_count}) must equal "
            f"evaluated_period_count ({result.evaluated_period_count})"
        )


def _collect_evaluation_inputs(
    outcomes: Iterable[object],
) -> tuple[list[FundReturnReconciliationResult], int, int]:
    successful_results: list[FundReturnReconciliationResult] = []
    missing_holdings_count = 0
    missing_fund_price_count = 0

    for outcome in outcomes:
        if isinstance(outcome, (HistoricalReconciliationRecord, HistoricalFxReconciliationRecord)):
            successful_results.append(outcome.result.reconciliation_result)
            continue

        if not isinstance(outcome, (SkippedReconciliationRecord, SkippedFxReconciliationRecord)):
            raise UnknownOutcomeError(f"Unsupported outcome type: {type(outcome).__name__}")

        if isinstance(outcome.reason, MissingHoldingsSkip):
            missing_holdings_count += 1
        elif isinstance(outcome.reason, MissingFundPriceSkip):
            missing_fund_price_count += 1
        else:
            raise UnknownSkipReasonError(
                f"Unsupported skip reason type: {type(outcome.reason).__name__}"
            )

    return successful_results, missing_holdings_count, missing_fund_price_count


def evaluate_historical_reconciliation_dataset(
    dataset: HistoricalReconciliationDataset | HistoricalFxReconciliationDataset,
) -> HistoricalReconciliationEvaluation:
    """Evaluate historical reconciliation outcomes using canonical Rust metrics."""
    if not isinstance(
        dataset,
        (HistoricalReconciliationDataset, HistoricalFxReconciliationDataset),
    ):
        raise UnsupportedHistoricalReconciliationDatasetError(
            f"Unsupported historical reconciliation dataset type: {type(dataset).__name__}"
        )

    successful_results, missing_holdings_count, missing_fund_price_count = (
        _collect_evaluation_inputs(dataset.outcomes)
    )

    evaluated_period_count = len(successful_results)
    skipped_period_count = missing_holdings_count + missing_fund_price_count
    total_period_count = evaluated_period_count + skipped_period_count

    metrics = (
        evaluate_reconciliation_metrics(successful_results) if evaluated_period_count > 0 else None
    )

    return HistoricalReconciliationEvaluation(
        metrics=metrics,
        total_period_count=total_period_count,
        evaluated_period_count=evaluated_period_count,
        skipped_period_count=skipped_period_count,
        missing_holdings_count=missing_holdings_count,
        missing_fund_price_count=missing_fund_price_count,
    )
