"""Explicit JSON serialization for historical reconciliation evaluation summaries."""

import json

from .evaluation import HistoricalReconciliationEvaluation

_SCHEMA_VERSION = 1


def serialize_historical_reconciliation_evaluation(
    evaluation: HistoricalReconciliationEvaluation,
) -> bytes:
    """Serialize a HistoricalReconciliationEvaluation as deterministic UTF-8 JSON bytes."""
    if not isinstance(evaluation, HistoricalReconciliationEvaluation):
        target_type = type(evaluation).__name__
        raise TypeError(
            f"evaluation must be a HistoricalReconciliationEvaluation instance, got {target_type}"
        )

    scope = evaluation.scope
    scope_payload = (
        None
        if scope is None
        else {
            "fund_id": scope.fund_id,
            "fund_price_source_id": scope.fund_price_source_id,
            "fx_source_id": scope.fx_source_id,
            "holdings_source_id": scope.holdings_source_id,
            "kind": scope.kind.value,
            "security_price_source_id": scope.security_price_source_id,
        }
    )

    metrics = evaluation.metrics
    metrics_payload = (
        None
        if metrics is None
        else {
            "full_return_coverage_ratio": metrics.full_return_coverage_ratio,
            "mean_absolute_residual_decimal": metrics.mean_absolute_residual,
            "mean_residual_decimal": metrics.mean_residual,
            "mean_return_coverage_ratio": metrics.mean_return_coverage,
            "root_mean_squared_residual_decimal": metrics.root_mean_squared_residual,
            "sample_count": metrics.sample_count,
        }
    )

    payload = {
        "counts": {
            "evaluated_period_count": evaluation.evaluated_period_count,
            "missing_fund_price_count": evaluation.missing_fund_price_count,
            "missing_holdings_count": evaluation.missing_holdings_count,
            "skipped_period_count": evaluation.skipped_period_count,
            "total_period_count": evaluation.total_period_count,
        },
        "metrics": metrics_payload,
        "schema_version": _SCHEMA_VERSION,
        "scope": scope_payload,
    }

    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
