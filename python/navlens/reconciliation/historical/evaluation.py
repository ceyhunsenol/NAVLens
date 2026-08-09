"""Evaluation orchestrator for historical reconciliation datasets."""

from collections.abc import Iterable
from dataclasses import dataclass

from navlens import (
    FundReturnReconciliationResult,
    ReconciliationMetrics,
    evaluate_reconciliation_metrics,
)

from ._scope_validation import (
    derive_outcome_scope,
    require_supported_outcome,
    validate_matching_scope,
)
from .dataset import HistoricalReconciliationDataset
from .errors import (
    InvalidHistoricalReconciliationEvaluationError,
    UnknownSkipReasonError,
    UnsupportedHistoricalReconciliationDatasetError,
)
from .fx_dataset import HistoricalFxReconciliationDataset
from .fx_outcome import HistoricalFxReconciliationRecord
from .outcome import (
    HistoricalReconciliationRecord,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
)
from .scope import HistoricalReconciliationEvaluationScope, HistoricalReconciliationKind


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationEvaluation:
    """Native reconciliation metrics and provenance for one homogeneous dataset."""

    metrics: ReconciliationMetrics | None
    scope: HistoricalReconciliationEvaluationScope | None
    total_period_count: int
    evaluated_period_count: int
    skipped_period_count: int
    missing_holdings_count: int
    missing_fund_price_count: int

    def __post_init__(self) -> None:
        """Validate count, scope, and native-metric relationships."""
        for name, value in (
            ("total_period_count", self.total_period_count),
            ("evaluated_period_count", self.evaluated_period_count),
            ("skipped_period_count", self.skipped_period_count),
            ("missing_holdings_count", self.missing_holdings_count),
            ("missing_fund_price_count", self.missing_fund_price_count),
        ):
            _validate_count(name, value)

        _validate_count_relationships(self)
        _validate_scope_relationship(self)
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


def _validate_scope_relationship(result: HistoricalReconciliationEvaluation) -> None:
    if result.total_period_count == 0:
        if result.scope is not None:
            raise InvalidHistoricalReconciliationEvaluationError(
                "scope must be None when total_period_count is 0"
            )
        return
    if result.scope is None:
        raise InvalidHistoricalReconciliationEvaluationError(
            "scope must be non-None when total_period_count > 0"
        )
    if not isinstance(result.scope, HistoricalReconciliationEvaluationScope):
        raise InvalidHistoricalReconciliationEvaluationError(
            "scope must be HistoricalReconciliationEvaluationScope, "
            f"got {type(result.scope).__name__}"
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
    expected_kind: HistoricalReconciliationKind,
) -> tuple[
    HistoricalReconciliationEvaluationScope | None,
    list[FundReturnReconciliationResult],
    int,
    int,
]:
    scope: HistoricalReconciliationEvaluationScope | None = None
    successful_results: list[FundReturnReconciliationResult] = []
    missing_holdings_count = 0
    missing_fund_price_count = 0

    for outcome in outcomes:
        typed_outcome = require_supported_outcome(outcome)
        outcome_scope = derive_outcome_scope(typed_outcome, expected_kind)
        if scope is None:
            scope = outcome_scope
        else:
            validate_matching_scope(scope, outcome_scope, typed_outcome.request.period)

        if isinstance(
            typed_outcome,
            (HistoricalReconciliationRecord, HistoricalFxReconciliationRecord),
        ):
            successful_results.append(typed_outcome.result.reconciliation_result)
        elif isinstance(typed_outcome.reason, MissingHoldingsSkip):
            missing_holdings_count += 1
        elif isinstance(typed_outcome.reason, MissingFundPriceSkip):
            missing_fund_price_count += 1
        else:
            raise UnknownSkipReasonError(
                f"Unsupported skip reason type: {type(typed_outcome.reason).__name__}"
            )

    return scope, successful_results, missing_holdings_count, missing_fund_price_count


def evaluate_historical_reconciliation_dataset(
    dataset: HistoricalReconciliationDataset | HistoricalFxReconciliationDataset,
) -> HistoricalReconciliationEvaluation:
    """Evaluate one homogeneous historical dataset using canonical Rust metrics."""
    if isinstance(dataset, HistoricalReconciliationDataset):
        expected_kind = HistoricalReconciliationKind.LEGACY
    elif isinstance(dataset, HistoricalFxReconciliationDataset):
        expected_kind = HistoricalReconciliationKind.FX_AWARE
    else:
        raise UnsupportedHistoricalReconciliationDatasetError(
            f"Unsupported historical reconciliation dataset type: {type(dataset).__name__}"
        )

    scope, successful_results, missing_holdings_count, missing_fund_price_count = (
        _collect_evaluation_inputs(dataset.outcomes, expected_kind)
    )
    evaluated_period_count = len(successful_results)
    skipped_period_count = missing_holdings_count + missing_fund_price_count
    metrics = evaluate_reconciliation_metrics(successful_results) if successful_results else None
    return HistoricalReconciliationEvaluation(
        metrics=metrics,
        scope=scope,
        total_period_count=evaluated_period_count + skipped_period_count,
        evaluated_period_count=evaluated_period_count,
        skipped_period_count=skipped_period_count,
        missing_holdings_count=missing_holdings_count,
        missing_fund_price_count=missing_fund_price_count,
    )
