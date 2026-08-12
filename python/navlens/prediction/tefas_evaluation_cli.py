"""Executable composition root for evaluating a stored TEFAS prediction."""

import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime

from navlens import NavlensValidationError
from navlens.sources.tefas import (
    AcquireTefasPrices,
    TefasHttpClient,
    TefasPriceRequest,
    TefasSourceError,
)

from .artifact import SingleReturnPredictionArtifact, load_single_return_prediction_artifact
from .errors import PredictionArtifactError
from .live_evaluation import LivePredictionEvaluationResult, evaluate_tefas_prediction_artifact
from .live_evaluation_output import (
    format_live_prediction_evaluation,
    serialize_live_prediction_evaluation,
)
from .output import publish_prediction_output
from .tefas_evaluation_cli_args import parse_tefas_prediction_evaluation_arguments


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire the realized NAV period and evaluate one stored prediction."""
    arguments = parse_tefas_prediction_evaluation_arguments(argv)
    evaluated_at = datetime.now(UTC).replace(microsecond=0)
    try:
        artifact = load_single_return_prediction_artifact(arguments.prediction_artifact)
        request = _build_request(artifact.fund_id, artifact, arguments.as_of)
        acquisition = AcquireTefasPrices(TefasHttpClient(), arguments.raw_root)
        acquired = acquisition.acquire(request, arguments.as_of, evaluated_at)
        result = evaluate_tefas_prediction_artifact(
            artifact,
            acquired,
            evaluated_at=evaluated_at,
        )
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except (OSError, PredictionArtifactError, TefasSourceError, NavlensValidationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _build_request(
    fund_id: str,
    artifact: SingleReturnPredictionArtifact,
    as_of: date,
) -> TefasPriceRequest:
    start_date = date.fromisoformat(str(artifact.last_observation_date))
    end_date = date.fromisoformat(str(artifact.target_date))
    if end_date > as_of:
        raise PredictionArtifactError(
            f"target date {end_date} is after evaluation as-of date {as_of}"
        )
    return TefasPriceRequest(fund_id, start_date, end_date)


def _render(result: LivePredictionEvaluationResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_live_prediction_evaluation(result)
    return format_live_prediction_evaluation(result).encode("utf-8")
