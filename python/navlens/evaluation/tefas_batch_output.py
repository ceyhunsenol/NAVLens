"""Compact CSV-compatible output for multi-fund backtests."""

import csv
from io import StringIO

from .comparison import ModelComparisonEntry
from .tefas_batch import BatchFundFailure, BatchFundSuccess, TefasBatchResult

HEADER = (
    "fund",
    "status",
    "model",
    "mae_decimal",
    "rmse_decimal",
    "direction_accuracy",
    "run_id",
    "manifest",
    "error_type",
    "error",
)


def format_tefas_batch_result(result: TefasBatchResult) -> str:
    """Render batch counts and one metrics row per successful model."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HEADER)
    for success in result.successes:
        for entry in success.completed.result.comparison.entries:
            writer.writerow(_success_row(success, entry))
    for failure in result.failures:
        writer.writerow(_failure_row(failure))
    table = output.getvalue().rstrip("\n")
    return "\n".join(
        [
            f"batch_total={result.total}",
            f"batch_succeeded={len(result.successes)}",
            f"batch_failed={len(result.failures)}",
            table,
        ]
    )


def _success_row(
    success: BatchFundSuccess,
    entry: ModelComparisonEntry,
) -> tuple[object, ...]:
    metrics = entry.result.metrics
    return (
        success.fund_code,
        "success",
        f"{entry.model_name}@{entry.model_version}",
        metrics.mean_absolute_error,
        metrics.root_mean_squared_error,
        metrics.direction_accuracy,
        success.completed.manifest.run_id,
        success.completed.manifest.path,
        "",
        "",
    )


def _failure_row(failure: BatchFundFailure) -> tuple[object, ...]:
    return (
        failure.fund_code,
        "failure",
        "",
        "",
        "",
        "",
        "",
        "",
        failure.error_type,
        failure.message,
    )
