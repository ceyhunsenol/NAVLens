"""Executable composition root for batch TEFAS prediction evaluation."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient

from .output import publish_prediction_output
from .tefas_evaluation_batch import (
    TefasPredictionEvaluationBatchResult,
    evaluate_tefas_prediction_artifacts,
    prediction_evaluation_batch_exit_code,
)
from .tefas_evaluation_batch_args import (
    parse_tefas_prediction_evaluation_batch_arguments,
)
from .tefas_evaluation_batch_output import (
    format_tefas_prediction_evaluation_batch,
    serialize_tefas_prediction_evaluation_batch,
)
from .tefas_evaluation_execution import EvaluateTefasPredictionArtifact


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_tefas_prediction_evaluation_batch_arguments(argv)
    evaluated_at = datetime.now(UTC).replace(microsecond=0)
    evaluator = EvaluateTefasPredictionArtifact(
        AcquireTefasPrices(TefasHttpClient(), arguments.raw_root),
        arguments.as_of,
        evaluated_at,
    )
    result = evaluate_tefas_prediction_artifacts(arguments.prediction_artifacts, evaluator)
    try:
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return prediction_evaluation_batch_exit_code(result)


def _render(result: TefasPredictionEvaluationBatchResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_tefas_prediction_evaluation_batch(result)
    return format_tefas_prediction_evaluation_batch(result).encode("utf-8")
