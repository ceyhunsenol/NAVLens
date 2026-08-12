"""Shared command-line options for the implemented prediction baseline."""

import argparse

from .options import PredictionModelOptions


def add_prediction_model_options(parser: argparse.ArgumentParser) -> None:
    """Add the shared baseline-model options to a command parser."""
    parser.add_argument("--lookback", type=_positive_integer, default=5)
    parser.add_argument("--minimum-training-returns", type=_positive_integer)
    parser.add_argument("--confidence-level", type=_confidence_level, default=0.90)
    parser.add_argument("--model-version", default="v1")


def prediction_model_options_from_namespace(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
) -> PredictionModelOptions:
    """Map parsed fields to a validated immutable settings record."""
    model_version = values.model_version.strip()
    if not model_version:
        parser.error("--model-version cannot be empty")
    return PredictionModelOptions(
        values.lookback,
        values.minimum_training_returns,
        values.confidence_level,
        model_version,
    )


def _positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a positive integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def _confidence_level(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("confidence level must be between 0 and 1") from error
    if not 0.0 < number < 1.0:
        raise argparse.ArgumentTypeError("confidence level must be between 0 and 1")
    return number
