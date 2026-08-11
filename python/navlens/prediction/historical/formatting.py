"""Deterministic text formatting for historical prediction evaluation summaries."""

from .evaluation import HistoricalPredictionEvaluation
from .scope import HistoricalPredictionEvaluationScope


def format_historical_prediction_evaluation(
    evaluation: HistoricalPredictionEvaluation,
) -> str:
    """Format a HistoricalPredictionEvaluation into a human-readable text report."""
    if not isinstance(evaluation, HistoricalPredictionEvaluation):
        target_type = type(evaluation).__name__
        raise TypeError(
            f"evaluation must be a HistoricalPredictionEvaluation instance, got {target_type}"
        )

    lines = [
        "Historical Prediction Evaluation",
        "================================",
    ]
    lines.extend(_format_scope_lines(evaluation.scope))
    lines.extend(_format_count_lines(evaluation))
    lines.extend(_format_metrics_lines(evaluation))
    lines.extend(_format_warning_lines(evaluation))

    return "\n".join(lines)


def _format_scope_lines(scope: HistoricalPredictionEvaluationScope | None) -> list[str]:
    if scope is None:
        return ["Scope: None", ""]

    return [
        "Scope:",
        f"  Fund ID: {scope.fund_id}",
        f"  Source ID: {scope.source_id}",
        f"  Lookback: {scope.lookback}",
        f"  Confidence Level: {scope.confidence_level}",
        f"  Model Version: {scope.model_version}",
        f"  Minimum Training Returns: {scope.minimum_training_returns}",
        "",
    ]


def _format_count_lines(evaluation: HistoricalPredictionEvaluation) -> list[str]:
    return [
        "Period Counts:",
        f"  Total Period Count: {evaluation.total_period_count}",
        f"  Evaluated Period Count: {evaluation.evaluated_period_count}",
        f"  Skipped Period Count: {evaluation.skipped_period_count}",
        f"  No Eligible Snapshots Count: {evaluation.no_eligible_snapshots_count}",
        f"  Insufficient History Count: {evaluation.insufficient_history_count}",
        f"  Target Not Yet Available Count: {evaluation.target_not_yet_available_count}",
        f"  Missing Target Observation Count: {evaluation.missing_target_observation_count}",
        "",
    ]


def _format_metrics_lines(evaluation: HistoricalPredictionEvaluation) -> list[str]:
    metrics = evaluation.metrics
    if metrics is None:
        return ["Backtest Metrics: Unavailable (0 evaluated periods)"]

    lines = [
        "Backtest Metrics:",
        f"  Sample Count: {metrics.sample_count}",
        f"  Mean Absolute Error (Decimal): {metrics.mean_absolute_error:.6f}",
        f"  Mean Error (Decimal): {metrics.mean_error:.6f}",
        f"  Root Mean Squared Error (Decimal): {metrics.root_mean_squared_error:.6f}",
        f"  Direction Accuracy (Ratio): {metrics.direction_accuracy:.6f}",
    ]

    interval = metrics.interval
    if interval is not None:
        lines.extend(
            [
                "Interval Metrics:",
                f"  Confidence Level: {interval.confidence_level}",
                f"  Sample Count: {interval.sample_count}",
                f"  Coverage (Ratio): {interval.coverage:.6f}",
                f"  Mean Width (Decimal): {interval.mean_width:.6f}",
            ]
        )

    return lines


def _format_warning_lines(evaluation: HistoricalPredictionEvaluation) -> list[str]:
    if evaluation.skipped_period_count > 0:
        return [
            "",
            f"WARNING: Skipped periods exist ({evaluation.skipped_period_count} of "
            f"{evaluation.total_period_count} periods skipped). Backtest metrics reflect "
            "evaluated periods only.",
        ]
    return []
