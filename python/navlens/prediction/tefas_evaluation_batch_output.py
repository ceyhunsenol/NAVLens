"""Deterministic output for batch evaluation of stored predictions."""

import csv
import json
from io import StringIO

from .artifact_schemas import TEFAS_PREDICTION_EVALUATION_BATCH_SCHEMA_VERSION
from .live_evaluation_output import serialize_live_prediction_evaluation
from .tefas_evaluation_batch import TefasPredictionEvaluationBatchResult


def format_tefas_prediction_evaluation_batch(
    result: TefasPredictionEvaluationBatchResult,
) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("artifact", "status", "fund_id", "target_date", "error_type", "error"))
    for success in result.successes:
        artifact = success.completed.artifact
        writer.writerow(
            (
                success.artifact_path,
                "success",
                artifact.fund_id,
                artifact.target_date,
                "",
                "",
            )
        )
    for failure in result.failures:
        writer.writerow(
            (
                failure.artifact_path,
                "failure",
                "",
                "",
                failure.error_type,
                failure.message,
            )
        )
    return "\n".join((*_summary(result), output.getvalue().rstrip("\n")))


def serialize_tefas_prediction_evaluation_batch(
    result: TefasPredictionEvaluationBatchResult,
) -> bytes:
    payload = {
        "failed_count": len(result.failures),
        "failures": [
            {
                "artifact_path": str(item.artifact_path),
                "error_type": item.error_type,
                "message": item.message,
            }
            for item in result.failures
        ],
        "schema_version": TEFAS_PREDICTION_EVALUATION_BATCH_SCHEMA_VERSION,
        "succeeded_count": len(result.successes),
        "successes": [
            json.loads(serialize_live_prediction_evaluation(item.completed))
            for item in result.successes
        ],
        "total_count": result.total,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def _summary(result: TefasPredictionEvaluationBatchResult) -> tuple[str, ...]:
    return (
        f"batch_total={result.total}",
        f"batch_succeeded={len(result.successes)}",
        f"batch_failed={len(result.failures)}",
    )
