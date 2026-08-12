"""Executable composition root for multi-fund TEFAS predictions."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient
from navlens.sources.tefas.batch import TefasBatchResult, batch_exit_code, run_tefas_batch

from .contracts import SingleReturnPredictionResult
from .output import publish_prediction_output
from .tefas_batch_args import parse_tefas_prediction_batch_arguments
from .tefas_batch_execution import ExecuteTefasPrediction
from .tefas_batch_output import (
    format_tefas_prediction_batch,
    serialize_tefas_prediction_batch,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run sequential per-fund predictions and report isolated failures."""
    arguments = parse_tefas_prediction_batch_arguments(argv)
    acquired_at = datetime.now(UTC).replace(microsecond=0)
    raw_root = arguments.acquisitions[0].raw_root
    executor = ExecuteTefasPrediction(
        AcquireTefasPrices(TefasHttpClient(), raw_root),
        acquired_at,
        arguments.options,
    )
    result = run_tefas_batch(arguments.acquisitions, executor)
    try:
        publish_prediction_output(
            _render(result, arguments.options.output_format),
            output_path=arguments.options.output_path,
            stdout=sys.stdout.buffer,
        )
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return batch_exit_code(result)


def _render(
    result: TefasBatchResult[SingleReturnPredictionResult],
    output_format: str,
) -> bytes:
    if output_format == "json":
        return serialize_tefas_prediction_batch(result)
    return format_tefas_prediction_batch(result).encode("utf-8")
