"""Deterministic text formatting for auditable historical prediction runs."""

from ._reporting import skip_reason_code
from .formatting import format_historical_prediction_evaluation
from .outcome import HistoricalPredictionRecord, SkippedPredictionRecord
from .run_result import HistoricalPredictionRunResult


def format_historical_prediction_run_result(result: HistoricalPredictionRunResult) -> str:
    """Format aggregate metrics and every ordered period outcome for audit."""
    if not isinstance(result, HistoricalPredictionRunResult):
        raise TypeError(
            f"result must be a HistoricalPredictionRunResult instance, got {type(result).__name__}"
        )

    summary = format_historical_prediction_evaluation(result.evaluation)
    outcome_lines = ["", "Period Outcomes:"]
    outcome_lines.extend(_format_outcome(outcome) for outcome in result.dataset.outcomes)
    return "\n".join([summary, *outcome_lines])


def _format_outcome(outcome: HistoricalPredictionRecord | SkippedPredictionRecord) -> str:
    period = f"{outcome.request.prediction_date} -> {outcome.request.target_date}"
    if isinstance(outcome, HistoricalPredictionRecord):
        return (
            f"  {period} | evaluated | predicted={outcome.predicted_return_decimal:.10f} | "
            f"realized={outcome.realized_return_decimal:.10f}"
        )
    return f"  {period} | skipped | reason={skip_reason_code(outcome.reason)}"
