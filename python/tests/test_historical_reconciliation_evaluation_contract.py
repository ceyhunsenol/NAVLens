"""Contract tests for historical reconciliation evaluation summaries."""

from collections.abc import Callable

import pytest
from navlens import ReconciliationMetrics
from navlens.reconciliation.historical import (
    HistoricalReconciliationEvaluation,
    InvalidHistoricalReconciliationEvaluationError,
    evaluate_historical_reconciliation_dataset,
)
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_legacy_dataset,
)


def _native_metrics() -> ReconciliationMetrics:
    evaluation = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())
    assert evaluation.metrics is not None
    return evaluation.metrics


def _valid_arguments() -> dict[str, object]:
    return {
        "metrics": _native_metrics(),
        "total_period_count": 2,
        "evaluated_period_count": 2,
        "skipped_period_count": 0,
        "missing_holdings_count": 0,
        "missing_fund_price_count": 0,
    }


def _construct(arguments: dict[str, object]) -> HistoricalReconciliationEvaluation:
    return HistoricalReconciliationEvaluation(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("total_period_count", True, "total_period_count must be a non-bool integer"),
        ("evaluated_period_count", 2.0, "evaluated_period_count must be a non-bool integer"),
        ("skipped_period_count", -1, "skipped_period_count must be non-negative"),
    ],
)
def test_rejects_invalid_count_values(field: str, value: object, message: str) -> None:
    arguments = _valid_arguments()
    arguments[field] = value

    with pytest.raises(InvalidHistoricalReconciliationEvaluationError, match=message):
        _construct(arguments)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda values: values.update(total_period_count=3),
            "must equal total_period_count",
        ),
        (
            lambda values: values.update(
                metrics=None,
                total_period_count=2,
                evaluated_period_count=0,
                skipped_period_count=2,
                missing_holdings_count=1,
            ),
            "must equal skipped_period_count",
        ),
    ],
)
def test_rejects_inconsistent_counts(
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    arguments = _valid_arguments()
    mutate(arguments)

    with pytest.raises(InvalidHistoricalReconciliationEvaluationError, match=message):
        _construct(arguments)


def test_rejects_metrics_when_no_period_was_evaluated() -> None:
    arguments = _valid_arguments()
    arguments.update(
        total_period_count=2,
        evaluated_period_count=0,
        skipped_period_count=2,
        missing_holdings_count=1,
        missing_fund_price_count=1,
    )

    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationError,
        match="metrics must be None when evaluated_period_count is 0",
    ):
        _construct(arguments)


def test_requires_metrics_when_periods_were_evaluated() -> None:
    arguments = _valid_arguments()
    arguments["metrics"] = None

    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationError,
        match="metrics must be non-None when evaluated_period_count > 0",
    ):
        _construct(arguments)


def test_rejects_invalid_metrics_type() -> None:
    arguments = _valid_arguments()
    arguments["metrics"] = "not_metrics"

    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationError,
        match="metrics must be ReconciliationMetrics",
    ):
        _construct(arguments)


def test_rejects_native_metrics_sample_count_mismatch() -> None:
    arguments = _valid_arguments()
    arguments.update(total_period_count=3, evaluated_period_count=3)

    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationError,
        match=r"metrics.sample_count .* must equal evaluated_period_count",
    ):
        _construct(arguments)
