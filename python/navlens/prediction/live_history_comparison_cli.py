"""Executable composition root for fair live model comparison."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError

from .errors import PredictionArtifactError
from .live_history_comparison import (
    LivePredictionHistoryComparisonResult,
    compare_live_prediction_histories,
)
from .live_history_comparison_cli_args import (
    parse_live_prediction_history_comparison_arguments,
)
from .live_history_comparison_output import (
    format_live_prediction_history_comparison,
    serialize_live_prediction_history_comparison,
)
from .live_history_loading import load_live_prediction_history
from .output import publish_prediction_output


def main(argv: Sequence[str] | None = None) -> int:
    """Load model-specific histories and report a fair native comparison."""
    arguments = parse_live_prediction_history_comparison_arguments(argv)
    try:
        histories = tuple(load_live_prediction_history(group) for group in arguments.histories)
        result = compare_live_prediction_histories(histories)
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except (OSError, PredictionArtifactError, NavlensValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _render(
    result: LivePredictionHistoryComparisonResult,
    output_format: str,
) -> bytes:
    if output_format == "json":
        return serialize_live_prediction_history_comparison(result)
    return format_live_prediction_history_comparison(result).encode("utf-8")
