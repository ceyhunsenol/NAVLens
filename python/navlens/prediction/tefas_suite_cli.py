"""Executable composition root for same-snapshot TEFAS model suites."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from navlens import NavlensValidationError
from navlens.datasets import FundUnitPriceDatasetError
from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient, TefasSourceError

from .errors import PointInTimePredictionError
from .model_suite import PredictionModelSuiteResult, predict_tefas_model_suite
from .model_suite_output import (
    format_prediction_model_suite,
    serialize_prediction_model_suite,
)
from .output import publish_prediction_output
from .tefas_suite_cli_args import parse_tefas_prediction_suite_arguments


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire once, run every baseline, and publish one suite artifact."""
    arguments = parse_tefas_prediction_suite_arguments(argv)
    acquired_at = datetime.now(UTC).replace(microsecond=0)
    try:
        acquisition = AcquireTefasPrices(TefasHttpClient(), arguments.acquisition.raw_root).acquire(
            arguments.acquisition.request, arguments.acquisition.as_of, acquired_at
        )
        result = predict_tefas_model_suite(
            acquisition,
            acquired_at=acquired_at,
            prediction_date=arguments.prediction_date,
            target_date=arguments.target_date,
            options=arguments.options,
            freshness=arguments.freshness,
        )
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


def _render(result: PredictionModelSuiteResult, output_format: str) -> bytes:
    if output_format == "json":
        return serialize_prediction_model_suite(result)
    return format_prediction_model_suite(result).encode("utf-8")
