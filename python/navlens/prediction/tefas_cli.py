"""Executable composition root for keyless TEFAS prediction."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from navlens import NavlensValidationError
from navlens.datasets import FundUnitPriceDatasetError
from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient, TefasSourceError

from .contracts import SingleReturnPredictionResult
from .errors import PointInTimePredictionError
from .output import publish_prediction_output
from .serialization import serialize_single_return_prediction
from .tefas import predict_next_published_nav_return_from_tefas_acquisition
from .tefas_cli_args import TefasPredictionCliArguments, parse_tefas_prediction_arguments
from .text_formatting import format_prediction_text


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire TEFAS prices, predict through the canonical pipeline, and report."""
    arguments = parse_tefas_prediction_arguments(argv)
    acquired_at = datetime.now(UTC).replace(microsecond=0)
    try:
        result = _predict(arguments, acquired_at)
        publish_prediction_output(
            _render(result, arguments.output_format),
            output_path=arguments.output_path,
            stdout=sys.stdout.buffer,
        )
    except (
        FundUnitPriceDatasetError,
        NavlensValidationError,
        PointInTimePredictionError,
        TefasSourceError,
        OSError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


def _predict(
    arguments: TefasPredictionCliArguments,
    acquired_at: datetime,
) -> SingleReturnPredictionResult:
    acquisition = AcquireTefasPrices(TefasHttpClient(), arguments.acquisition.raw_root)
    acquired = acquisition.acquire(
        arguments.acquisition.request,
        arguments.acquisition.as_of,
        acquired_at,
    )
    return predict_next_published_nav_return_from_tefas_acquisition(
        acquired,
        acquired_at=acquired_at,
        prediction_date=arguments.prediction_date,
        target_date=arguments.target_date,
        model=arguments.model,
        freshness=arguments.freshness,
    )


def _render(result: SingleReturnPredictionResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_single_return_prediction(result)
    return format_prediction_text(result).encode("utf-8")
