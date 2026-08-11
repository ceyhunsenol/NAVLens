"""Deterministic JSON serialization for auditable historical prediction runs."""

from typing import Any

from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot

from ._reporting import skip_reason_code
from .outcome import HistoricalPredictionRecord, SkippedPredictionRecord
from .run_result import HistoricalPredictionRunResult
from .serialization import _encode_json, _evaluation_payload

_SCHEMA_VERSION = 1


def serialize_historical_prediction_run_result(
    result: HistoricalPredictionRunResult,
) -> bytes:
    """Serialize aggregate metrics and ordered period audit records as JSON."""
    if not isinstance(result, HistoricalPredictionRunResult):
        raise TypeError(
            f"result must be a HistoricalPredictionRunResult instance, got {type(result).__name__}"
        )
    return _encode_json(
        {
            "evaluation": _evaluation_payload(result.evaluation),
            "outcomes": [_outcome_payload(outcome) for outcome in result.dataset.outcomes],
            "schema_version": _SCHEMA_VERSION,
        }
    )


def _outcome_payload(
    outcome: HistoricalPredictionRecord | SkippedPredictionRecord,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "request": _request_payload(outcome),
        "status": "evaluated" if isinstance(outcome, HistoricalPredictionRecord) else "skipped",
    }
    if isinstance(outcome, HistoricalPredictionRecord):
        payload["prediction"] = _prediction_payload(outcome)
        payload["realized"] = _realized_payload(outcome)
    else:
        payload["reason"] = skip_reason_code(outcome.reason)
    return payload


def _request_payload(
    outcome: HistoricalPredictionRecord | SkippedPredictionRecord,
) -> dict[str, str]:
    request = outcome.request
    return {
        "evaluation_timestamp": request.evaluation_timestamp.isoformat(),
        "prediction_date": str(request.prediction_date),
        "prediction_timestamp": request.prediction_timestamp.isoformat(),
        "pricing_as_of_date": str(request.pricing_as_of_date),
        "target_date": str(request.target_date),
    }


def _prediction_payload(outcome: HistoricalPredictionRecord) -> dict[str, Any]:
    result = outcome.prediction_result
    return {
        "confidence_level": result.confidence_level,
        "expected_return_decimal": result.expected_return_decimal,
        "feature_schema_version": result.feature_schema_version,
        "interval_lower_decimal": result.prediction_interval_lower_decimal,
        "interval_upper_decimal": result.prediction_interval_upper_decimal,
        "last_observation_available_at": result.last_observation_available_at.isoformat(),
        "last_observation_date": str(result.last_observation_date),
        "last_observation_ingested_at": result.last_observation_ingested_at.isoformat(),
        "model_name": result.model_name,
        "model_version": result.model_version,
    }


def _realized_payload(outcome: HistoricalPredictionRecord) -> dict[str, Any]:
    return {
        "end_snapshot": _snapshot_payload(outcome.realized_end_snapshot),
        "period_end_date": str(outcome.realized_period_return.period_end_date),
        "period_start_date": str(outcome.realized_period_return.period_start_date),
        "return_decimal": outcome.realized_return_decimal,
        "start_snapshot": _snapshot_payload(outcome.realized_start_snapshot),
    }


def _snapshot_payload(snapshot: FundUnitPriceSnapshot) -> dict[str, Any]:
    return {
        "available_at": snapshot.available_at.isoformat(),
        "fund_id": snapshot.fund_id,
        "ingested_at": snapshot.ingested_at.isoformat(),
        "market_date": str(snapshot.observation.date),
        "source_id": snapshot.source_id,
        "unit_price_decimal": snapshot.observation.unit_price.value,
    }
