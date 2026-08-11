"""Output stream writer for historical prediction evaluations."""

from typing import BinaryIO, TextIO

from .historical import (
    HistoricalPredictionRunResult,
    format_historical_prediction_run_result,
    serialize_historical_prediction_run_result,
)


def write_historical_prediction_run_result(
    result: HistoricalPredictionRunResult,
    output_format: str,
    *,
    text_stream: TextIO,
    binary_stream: BinaryIO,
) -> None:
    """Write an auditable historical prediction run to the requested stream."""
    if output_format == "json":
        binary_stream.write(serialize_historical_prediction_run_result(result))
    elif output_format == "text":
        text_stream.write(format_historical_prediction_run_result(result) + "\n")
    else:
        raise ValueError(f"unsupported output format: {output_format!r}")
