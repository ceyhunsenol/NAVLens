"""Executable composition root for evaluating a stored TEFAS prediction."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from navlens import NavlensValidationError
from navlens.sources.tefas import (
    AcquireTefasPrices,
    TefasHttpClient,
    TefasSourceError,
)

from .artifact import load_single_return_prediction_artifact
from .errors import PredictionArtifactError
from .live_evaluation import LivePredictionEvaluationResult
from .live_evaluation_output import (
    format_live_prediction_evaluation,
    serialize_live_prediction_evaluation,
)
from .output import publish_prediction_output
from .tefas_evaluation_cli_args import parse_tefas_prediction_evaluation_arguments
from .tefas_evaluation_execution import EvaluateTefasPredictionArtifact


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire the realized NAV period and evaluate one stored prediction."""
    arguments = parse_tefas_prediction_evaluation_arguments(argv)
    evaluated_at = datetime.now(UTC).replace(microsecond=0)
    try:
        evaluator = EvaluateTefasPredictionArtifact(
            AcquireTefasPrices(TefasHttpClient(), arguments.raw_root),
            arguments.as_of,
            evaluated_at,
        )
        artifact = load_single_return_prediction_artifact(arguments.prediction_artifact)
        result = evaluator.evaluate(artifact)
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except (OSError, PredictionArtifactError, TefasSourceError, NavlensValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _render(result: LivePredictionEvaluationResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_live_prediction_evaluation(result)
    return format_live_prediction_evaluation(result).encode("utf-8")
