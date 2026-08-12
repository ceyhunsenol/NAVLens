"""Deterministic text and JSON output for TEFAS prediction batches."""

import csv
import json
from io import StringIO

from navlens.sources.tefas.batch import (
    TefasBatchFailure,
    TefasBatchResult,
    TefasBatchSuccess,
)

from .artifact_schemas import TEFAS_PREDICTION_BATCH_SCHEMA_VERSION
from .contracts import SingleReturnPredictionResult
from .serialization import serialize_single_return_prediction

SCHEMA_VERSION = TEFAS_PREDICTION_BATCH_SCHEMA_VERSION
HEADER = (
    "fund",
    "status",
    "prediction_date",
    "pricing_as_of_date",
    "target_date",
    "expected_return_decimal",
    "interval_lower_decimal",
    "interval_upper_decimal",
    "confidence_level",
    "model",
    "error_type",
    "error",
)


def format_tefas_prediction_batch(result: TefasBatchResult[SingleReturnPredictionResult]) -> str:
    """Render summary counts and one CSV-compatible row per fund."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(_success_row(success) for success in result.successes)
    writer.writerows(_failure_row(failure) for failure in result.failures)
    return "\n".join([*_summary_lines(result), output.getvalue().rstrip("\n")])


def serialize_tefas_prediction_batch(
    result: TefasBatchResult[SingleReturnPredictionResult],
) -> bytes:
    """Serialize a batch result using a versioned deterministic JSON schema."""
    payload = {
        "failed_count": len(result.failures),
        "failures": [_failure_payload(item) for item in result.failures],
        "schema_version": SCHEMA_VERSION,
        "succeeded_count": len(result.successes),
        "successes": [_success_payload(item) for item in result.successes],
        "total_count": result.total,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def _summary_lines(result: TefasBatchResult[SingleReturnPredictionResult]) -> tuple[str, ...]:
    return (
        f"batch_total={result.total}",
        f"batch_succeeded={len(result.successes)}",
        f"batch_failed={len(result.failures)}",
    )


def _success_row(
    success: TefasBatchSuccess[SingleReturnPredictionResult],
) -> tuple[object, ...]:
    result = success.completed
    return (
        success.fund_code,
        "success",
        result.prediction_date,
        result.pricing_as_of_date,
        result.target_date,
        result.expected_return_decimal,
        result.prediction_interval_lower_decimal,
        result.prediction_interval_upper_decimal,
        result.confidence_level,
        f"{result.model_name}@{result.model_version}",
        "",
        "",
    )


def _failure_row(failure: TefasBatchFailure) -> tuple[object, ...]:
    return (
        failure.fund_code,
        "failure",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        failure.error_type,
        failure.message,
    )


def _success_payload(
    success: TefasBatchSuccess[SingleReturnPredictionResult],
) -> dict[str, object]:
    return json.loads(serialize_single_return_prediction(success.completed))


def _failure_payload(failure: TefasBatchFailure) -> dict[str, str]:
    return {
        "error_type": failure.error_type,
        "fund_id": failure.fund_code,
        "message": failure.message,
    }
