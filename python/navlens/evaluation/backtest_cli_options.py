"""Shared CLI mapping for walk-forward estimator and run storage options."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from navlens.sources.tefas.cli_arguments import positive_integer

from .linear_baseline import LinearBaselineWalkForward


@dataclass(frozen=True, slots=True)
class BacktestCliOptions:
    """Validated model configuration and manifest destination."""

    estimator: LinearBaselineWalkForward
    run_root: Path


def add_backtest_cli_options(parser: argparse.ArgumentParser) -> None:
    """Add shared estimator and manifest flags to a parser."""
    parser.add_argument("--lookback", type=positive_integer, default=5, metavar="N")
    parser.add_argument("--model-version", default="0.1.0")
    parser.add_argument("--confidence-level", type=_confidence_level, default=0.90)
    parser.add_argument("--minimum-training-returns", type=positive_integer)
    parser.add_argument("--run-root", type=Path, default=Path("data/runs"))


def backtest_cli_options_from_namespace(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
) -> BacktestCliOptions:
    """Build validated estimator and storage options from parsed values."""
    try:
        estimator = LinearBaselineWalkForward(
            lookback=values.lookback,
            model_version=values.model_version,
            confidence_level=values.confidence_level,
            minimum_training_returns=values.minimum_training_returns,
        )
    except ValueError as error:
        parser.error(str(error))
    return BacktestCliOptions(estimator, values.run_root)


def _confidence_level(value: str) -> float:
    try:
        confidence_level = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("confidence level must be a number") from error
    if not 0.0 < confidence_level < 1.0:
        raise argparse.ArgumentTypeError("confidence level must be between zero and one")
    return confidence_level
