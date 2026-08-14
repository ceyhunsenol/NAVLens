"""Executable composition root for failure-isolated multi-fund history comparison."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError

from .errors import PredictionArtifactError
from .live_history_comparison_batch import (
    LivePredictionHistoryComparisonBatchResult,
    compare_live_prediction_history_batches,
    live_prediction_history_comparison_batch_exit_code,
)
from .live_history_comparison_batch_args import (
    parse_live_prediction_history_comparison_batch_arguments,
)
from .live_history_comparison_batch_output import (
    format_live_prediction_history_comparison_batch,
    serialize_live_prediction_history_comparison_batch,
)
from .output import publish_prediction_output


def main(argv: Sequence[str] | None = None) -> int:
    """Execute multi-fund history comparison with per-scope failure isolation."""
    arguments = parse_live_prediction_history_comparison_batch_arguments(argv)
    try:
        result = compare_live_prediction_history_batches(arguments.evaluation_artifacts)
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
        return live_prediction_history_comparison_batch_exit_code(result)
    except (OSError, PredictionArtifactError, NavlensValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _render(
    result: LivePredictionHistoryComparisonBatchResult,
    output_format: str,
) -> bytes:
    if output_format == "json":
        return serialize_live_prediction_history_comparison_batch(result)
    return format_live_prediction_history_comparison_batch(result).encode("utf-8")
