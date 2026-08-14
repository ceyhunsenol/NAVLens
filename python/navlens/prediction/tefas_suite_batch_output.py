"""Deterministic text and JSON output for multi-fund TEFAS model-suite batches."""

import csv
import json
from io import StringIO

from navlens.sources.tefas.batch import (
    TefasBatchFailure,
    TefasBatchResult,
    TefasBatchSuccess,
)

from .artifact_schemas import TEFAS_PREDICTION_MODEL_SUITE_BATCH_SCHEMA_VERSION
from .model_suite import PredictionModelSuiteResult
from .model_suite_output import serialize_prediction_model_suite

HEADER = (
    "fund",
    "status",
    "prediction_date",
    "target_date",
    "models",
    "error_type",
    "error",
)


def format_tefas_prediction_suite_batch(
    result: TefasBatchResult[PredictionModelSuiteResult],
) -> str:
    """Render summary counts and one CSV-compatible audit row per fund."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(_success_row(item) for item in result.successes)
    writer.writerows(_failure_row(item) for item in result.failures)
    return "\n".join([*_summary_lines(result), output.getvalue().rstrip("\n")])


def serialize_tefas_prediction_suite_batch(
    result: TefasBatchResult[PredictionModelSuiteResult],
) -> bytes:
    """Serialize multi-fund suite batch results using a versioned deterministic JSON schema."""
    payload = {
        "failed_count": len(result.failures),
        "failures": [_failure_payload(item) for item in result.failures],
        "schema_version": TEFAS_PREDICTION_MODEL_SUITE_BATCH_SCHEMA_VERSION,
        "succeeded_count": len(result.successes),
        "successes": [
            json.loads(serialize_prediction_model_suite(item.completed))
            for item in result.successes
        ],
        "total_count": result.total,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def _summary_lines(
    result: TefasBatchResult[PredictionModelSuiteResult],
) -> tuple[str, ...]:
    return (
        f"batch_total={result.total}",
        f"batch_succeeded={len(result.successes)}",
        f"batch_failed={len(result.failures)}",
    )


def _success_row(
    success: TefasBatchSuccess[PredictionModelSuiteResult],
) -> tuple[object, ...]:
    first = success.completed.predictions[0]
    models = ",".join(item.model_name for item in success.completed.predictions)
    return (
        success.fund_code,
        "success",
        first.prediction_date,
        first.target_date,
        models,
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
        failure.error_type,
        failure.message,
    )


def _failure_payload(failure: TefasBatchFailure) -> dict[str, str]:
    return {
        "error_type": failure.error_type,
        "fund_id": failure.fund_code,
        "message": failure.message,
    }
