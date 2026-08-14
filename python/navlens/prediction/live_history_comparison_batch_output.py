"""Deterministic text and JSON output for multi-scope prediction history comparison."""

import json
from typing import Any

from .artifact_schemas import LIVE_PREDICTION_HISTORY_COMPARISON_BATCH_SCHEMA_VERSION
from .live_history_comparison_batch import (
    LivePredictionHistoryComparisonBatchOutcome,
    LivePredictionHistoryComparisonBatchResult,
    LivePredictionHistoryComparisonBatchSuccess,
)
from .live_history_comparison_output import (
    format_live_prediction_history_comparison,
    serialize_live_prediction_history_comparison,
)


def format_live_prediction_history_comparison_batch(
    result: LivePredictionHistoryComparisonBatchResult,
) -> str:
    """Format ordered multi-scope comparison outcomes as human-readable text."""
    summary = "\n".join(
        (
            f"batch_total={result.total_count}",
            f"batch_succeeded={result.succeeded_count}",
            f"batch_failed={result.failed_count}",
        )
    )
    outcomes = tuple(_format_outcome(outcome) for outcome in result.outcomes)
    return "\n\n".join((summary, *outcomes))


def serialize_live_prediction_history_comparison_batch(
    result: LivePredictionHistoryComparisonBatchResult,
) -> bytes:
    """Serialize ordered multi-scope comparison outcomes to versioned JSON bytes."""
    payload = {
        "failed_count": result.failed_count,
        "outcomes": [_serialize_outcome(item) for item in result.outcomes],
        "schema_version": LIVE_PREDICTION_HISTORY_COMPARISON_BATCH_SCHEMA_VERSION,
        "succeeded_count": result.succeeded_count,
        "total_count": result.total_count,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def _format_outcome(outcome: LivePredictionHistoryComparisonBatchOutcome) -> str:
    if isinstance(outcome, LivePredictionHistoryComparisonBatchSuccess):
        formatted = format_live_prediction_history_comparison(outcome.comparison)
        return f"--- Scope {outcome.fund_id}:{outcome.source_id} [success] ---\n{formatted}"
    return (
        f"--- Scope {outcome.fund_id}:{outcome.source_id} [failure] ---\n"
        f"reason_code={outcome.reason_code.value}\n"
        f"error_type={outcome.error_type}\n"
        f"message={outcome.message}"
    )


def _serialize_outcome(
    outcome: LivePredictionHistoryComparisonBatchOutcome,
) -> dict[str, Any]:
    if isinstance(outcome, LivePredictionHistoryComparisonBatchSuccess):
        return {
            "comparison": json.loads(
                serialize_live_prediction_history_comparison(outcome.comparison)
            ),
            "fund_id": outcome.fund_id,
            "source_id": outcome.source_id,
            "status": "success",
        }
    return {
        "error_type": outcome.error_type,
        "fund_id": outcome.fund_id,
        "message": outcome.message,
        "reason_code": outcome.reason_code.value,
        "source_id": outcome.source_id,
        "status": "failure",
    }
