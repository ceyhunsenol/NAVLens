"""Executable composition root for live prediction history reporting."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError

from .errors import PredictionArtifactError
from .live_history import LivePredictionHistoryResult
from .live_history_cli_args import parse_live_prediction_history_arguments
from .live_history_loading import load_live_prediction_history
from .live_history_output import (
    format_live_prediction_history,
    serialize_live_prediction_history,
)
from .output import publish_prediction_output


def main(argv: Sequence[str] | None = None) -> int:
    """Load explicit evaluation artifacts and report canonical aggregate metrics."""
    arguments = parse_live_prediction_history_arguments(argv)
    try:
        result = load_live_prediction_history(arguments.evaluation_artifacts)
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except (OSError, PredictionArtifactError, NavlensValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _render(result: LivePredictionHistoryResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_live_prediction_history(result)
    return format_live_prediction_history(result).encode("utf-8")
