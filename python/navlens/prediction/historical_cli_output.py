"""Output stream writer for historical prediction evaluations."""

from typing import BinaryIO, TextIO

from .historical import (
    HistoricalPredictionEvaluation,
    format_historical_prediction_evaluation,
    serialize_historical_prediction_evaluation,
)


def write_historical_prediction_evaluation(
    evaluation: HistoricalPredictionEvaluation,
    output_format: str,
    *,
    text_stream: TextIO,
    binary_stream: BinaryIO,
) -> None:
    """Write an evaluation to the requested output stream."""
    if output_format == "json":
        binary_stream.write(serialize_historical_prediction_evaluation(evaluation))
    elif output_format == "text":
        text_stream.write(format_historical_prediction_evaluation(evaluation) + "\n")
    else:
        raise ValueError(f"unsupported output format: {output_format!r}")
