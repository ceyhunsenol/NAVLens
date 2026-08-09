"""Deterministic text formatting for historical reconciliation evaluation summaries."""

from .evaluation import HistoricalReconciliationEvaluation
from .scope import HistoricalReconciliationKind


def format_historical_reconciliation_evaluation(
    evaluation: HistoricalReconciliationEvaluation,
) -> str:
    """Format a HistoricalReconciliationEvaluation into a human-readable text report."""
    if not isinstance(evaluation, HistoricalReconciliationEvaluation):
        target_type = type(evaluation).__name__
        raise TypeError(
            f"evaluation must be a HistoricalReconciliationEvaluation instance, got {target_type}"
        )

    lines = [
        "Historical Reconciliation Evaluation",
        "====================================",
    ]
    lines.extend(_format_scope_lines(evaluation))
    lines.extend(_format_count_lines(evaluation))
    lines.extend(_format_metrics_lines(evaluation))
    lines.extend(_format_warning_lines(evaluation))

    return "\n".join(lines)


def _format_scope_lines(evaluation: HistoricalReconciliationEvaluation) -> list[str]:
    scope = evaluation.scope
    if scope is None:
        return ["Scope: None", ""]

    kind_label = "Legacy" if scope.kind == HistoricalReconciliationKind.LEGACY else "FX-Aware"
    lines = [
        f"Scope Kind: {kind_label}",
        f"Fund ID: {scope.fund_id}",
        f"Holdings Source ID: {scope.holdings_source_id}",
        f"Security Price Source ID: {scope.security_price_source_id}",
        f"Fund Price Source ID: {scope.fund_price_source_id}",
    ]
    if scope.kind == HistoricalReconciliationKind.FX_AWARE and scope.fx_source_id is not None:
        lines.append(f"FX Source ID: {scope.fx_source_id}")
    lines.append("")
    return lines


def _format_count_lines(evaluation: HistoricalReconciliationEvaluation) -> list[str]:
    return [
        "Period Counts:",
        f"  Total Period Count: {evaluation.total_period_count}",
        f"  Evaluated Period Count: {evaluation.evaluated_period_count}",
        f"  Skipped Period Count: {evaluation.skipped_period_count}",
        f"  Missing Holdings Count: {evaluation.missing_holdings_count}",
        f"  Missing Fund Price Count: {evaluation.missing_fund_price_count}",
        "",
    ]


def _format_metrics_lines(evaluation: HistoricalReconciliationEvaluation) -> list[str]:
    metrics = evaluation.metrics
    if metrics is None:
        return ["Reconciliation Metrics: Unavailable (0 evaluated periods)"]

    return [
        "Reconciliation Metrics:",
        f"  Sample Count: {metrics.sample_count}",
        f"  Mean Absolute Residual (Decimal): {metrics.mean_absolute_residual:.6f}",
        f"  Mean Residual (Decimal): {metrics.mean_residual:.6f}",
        f"  Root Mean Squared Residual (Decimal): {metrics.root_mean_squared_residual:.6f}",
        f"  Mean Return Coverage (Ratio): {metrics.mean_return_coverage:.6f}",
        f"  Full Return Coverage (Ratio): {metrics.full_return_coverage_ratio:.6f}",
    ]


def _format_warning_lines(evaluation: HistoricalReconciliationEvaluation) -> list[str]:
    warnings: list[str] = []

    if evaluation.skipped_period_count > 0:
        warnings.extend(
            [
                "",
                f"WARNING: Skipped periods exist ({evaluation.skipped_period_count} of "
                f"{evaluation.total_period_count} periods skipped). Reconciliation metrics reflect "
                "evaluated periods only.",
            ]
        )

    metrics = evaluation.metrics
    if metrics is not None and metrics.full_return_coverage_ratio < 1.0:
        warnings.extend(
            [
                "",
                "WARNING: Some evaluated periods do not have full return coverage.",
                "Aggregate reconciliation metrics include partially covered periods and "
                "must not be interpreted as pure prediction error or alpha.",
            ]
        )

    return warnings
