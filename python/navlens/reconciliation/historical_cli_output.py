"""Output stream writer for historical reconciliation evaluations."""

from typing import BinaryIO, TextIO

from .historical.evaluation import HistoricalReconciliationEvaluation
from .historical.formatting import format_historical_reconciliation_evaluation
from .historical.serialization import serialize_historical_reconciliation_evaluation


def write_historical_reconciliation_evaluation(
    evaluation: HistoricalReconciliationEvaluation,
    output_format: str,
    *,
    text_stream: TextIO,
    binary_stream: BinaryIO,
) -> None:
    """Write evaluation report to provided text or binary output stream."""
    if output_format == "json":
        binary_stream.write(serialize_historical_reconciliation_evaluation(evaluation))
    elif output_format == "text":
        text_stream.write(format_historical_reconciliation_evaluation(evaluation) + "\n")
    else:
        raise ValueError(f"unsupported output format: {output_format!r}")
