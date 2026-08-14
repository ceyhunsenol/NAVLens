"""Failure-isolated multi-fund comparison for live prediction histories."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from navlens import NavlensValidationError

from .artifact import LivePredictionEvaluationArtifact
from .errors import (
    InvalidLivePredictionHistoryComparisonError,
    InvalidLivePredictionHistoryError,
)
from .live_history import evaluate_live_prediction_history
from .live_history_comparison import (
    LivePredictionHistoryComparisonResult,
    compare_live_prediction_histories,
)
from .live_history_grouping import (
    _group_artifacts_by_model,
    _group_artifacts_by_scope,
    _load_evaluation_artifacts_single_pass,
)


class LivePredictionHistoryComparisonScopeFailureReason(StrEnum):
    """Stable reason codes for per-scope comparison failures."""

    INVALID_HISTORY = "invalid_history"
    INVALID_COMPARISON = "invalid_comparison"
    NATIVE_VALIDATION = "native_validation"


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonBatchSuccess:
    """Successful comparison result for one (fund_id, source_id) scope."""

    fund_id: str
    source_id: str
    comparison: LivePredictionHistoryComparisonResult

    def __post_init__(self) -> None:
        _require_non_empty_string(self.fund_id, "fund_id")
        _require_non_empty_string(self.source_id, "source_id")
        if not isinstance(self.comparison, LivePredictionHistoryComparisonResult):
            raise ValueError("comparison must be a LivePredictionHistoryComparisonResult")
        if self.fund_id != self.comparison.fund_id or self.source_id != self.comparison.source_id:
            raise ValueError("success fund_id and source_id must match comparison scope")


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonBatchFailure:
    """Isolated failure for one (fund_id, source_id) scope."""

    fund_id: str
    source_id: str
    reason_code: LivePredictionHistoryComparisonScopeFailureReason
    error_type: str
    message: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.fund_id, "fund_id")
        _require_non_empty_string(self.source_id, "source_id")
        if not isinstance(self.reason_code, LivePredictionHistoryComparisonScopeFailureReason):
            raise ValueError(
                "reason_code must be a LivePredictionHistoryComparisonScopeFailureReason"
            )
        _require_non_empty_string(self.error_type, "error_type")
        _require_non_empty_string(self.message, "message")


LivePredictionHistoryComparisonBatchOutcome = (
    LivePredictionHistoryComparisonBatchSuccess | LivePredictionHistoryComparisonBatchFailure
)
_ScopeComparisonError = (
    InvalidLivePredictionHistoryError
    | InvalidLivePredictionHistoryComparisonError
    | NavlensValidationError
)


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonBatchResult:
    """Ordered outcomes for multi-scope live history comparison."""

    outcomes: tuple[LivePredictionHistoryComparisonBatchOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcomes, tuple) or not self.outcomes:
            raise ValueError("outcomes must be a non-empty tuple")
        for item in self.outcomes:
            if not isinstance(
                item,
                (
                    LivePredictionHistoryComparisonBatchSuccess,
                    LivePredictionHistoryComparisonBatchFailure,
                ),
            ):
                raise ValueError("outcomes items must be typed batch outcome instances")

    @property
    def successes(self) -> tuple[LivePredictionHistoryComparisonBatchSuccess, ...]:
        return tuple(
            item
            for item in self.outcomes
            if isinstance(item, LivePredictionHistoryComparisonBatchSuccess)
        )

    @property
    def failures(self) -> tuple[LivePredictionHistoryComparisonBatchFailure, ...]:
        return tuple(
            item
            for item in self.outcomes
            if isinstance(item, LivePredictionHistoryComparisonBatchFailure)
        )

    @property
    def total_count(self) -> int:
        return len(self.outcomes)

    @property
    def succeeded_count(self) -> int:
        return len(self.successes)

    @property
    def failed_count(self) -> int:
        return len(self.failures)


def compare_live_prediction_history_batches(
    paths: Iterable[Path | str],
) -> LivePredictionHistoryComparisonBatchResult:
    """Load evaluation artifacts, group by scope and model, and isolate scope failures."""
    artifacts = _load_evaluation_artifacts_single_pass(paths)
    scopes = _group_artifacts_by_scope(artifacts)

    outcomes: list[LivePredictionHistoryComparisonBatchOutcome] = []
    for (fund_id, source_id), scope_artifacts in scopes.items():
        outcomes.append(_compare_scope(fund_id, source_id, scope_artifacts))

    return LivePredictionHistoryComparisonBatchResult(tuple(outcomes))


def _compare_scope(
    fund_id: str,
    source_id: str,
    artifacts: Iterable[LivePredictionEvaluationArtifact],
) -> LivePredictionHistoryComparisonBatchOutcome:
    try:
        model_groups = _group_artifacts_by_model(artifacts)
        histories = tuple(
            evaluate_live_prediction_history(tuple(group)) for group in model_groups.values()
        )
        comparison = compare_live_prediction_histories(histories)
        return LivePredictionHistoryComparisonBatchSuccess(fund_id, source_id, comparison)
    except (
        InvalidLivePredictionHistoryError,
        InvalidLivePredictionHistoryComparisonError,
        NavlensValidationError,
    ) as error:
        return LivePredictionHistoryComparisonBatchFailure(
            fund_id,
            source_id,
            _map_scope_failure_reason(error),
            type(error).__name__,
            str(error),
        )


def _map_scope_failure_reason(
    error: _ScopeComparisonError,
) -> LivePredictionHistoryComparisonScopeFailureReason:
    """Map domain/validation exception types to stable reason codes."""
    if isinstance(error, InvalidLivePredictionHistoryError):
        return LivePredictionHistoryComparisonScopeFailureReason.INVALID_HISTORY
    if isinstance(error, InvalidLivePredictionHistoryComparisonError):
        return LivePredictionHistoryComparisonScopeFailureReason.INVALID_COMPARISON
    if isinstance(error, NavlensValidationError):
        return LivePredictionHistoryComparisonScopeFailureReason.NATIVE_VALIDATION
    raise TypeError("unsupported scope comparison error") from error


def live_prediction_history_comparison_batch_exit_code(
    result: LivePredictionHistoryComparisonBatchResult,
) -> int:
    """Determine standard exit code (0 = all success, 2 = partial, 1 = all failure)."""
    if not result.failures:
        return 0
    return 2 if result.successes else 1


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
