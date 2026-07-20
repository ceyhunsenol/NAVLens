"""Command-line input mapping for TEFAS walk-forward backtests."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    build_tefas_cli_parser,
    positive_integer,
    tefas_cli_arguments_from_namespace,
)

from .linear_baseline import LinearBaselineWalkForward


@dataclass(frozen=True, slots=True)
class TefasBacktestCliArguments:
    """Validated acquisition and estimator settings for one CLI run."""

    acquisition: TefasCliArguments
    estimator: LinearBaselineWalkForward
    run_root: Path


def parse_tefas_backtest_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasBacktestCliArguments:
    """Map command strings into explicit acquisition and estimator contracts."""
    current_date = today or date.today()
    parser = build_tefas_cli_parser(
        today=current_date,
        prog="navlens-backtest-tefas",
        description="Run an expanding-window baseline backtest on TEFAS prices.",
    )
    parser.add_argument("--lookback", type=positive_integer, default=5, metavar="N")
    parser.add_argument("--model-version", default="0.1.0")
    parser.add_argument("--confidence-level", type=_confidence_level, default=0.90)
    parser.add_argument("--minimum-training-returns", type=positive_integer)
    parser.add_argument("--run-root", type=Path, default=Path("data/runs"))
    values = parser.parse_args(argv)
    acquisition = tefas_cli_arguments_from_namespace(parser, values, current_date)
    try:
        estimator = LinearBaselineWalkForward(
            lookback=values.lookback,
            model_version=values.model_version,
            confidence_level=values.confidence_level,
            minimum_training_returns=values.minimum_training_returns,
        )
    except ValueError as error:
        parser.error(str(error))
    return TefasBacktestCliArguments(acquisition, estimator, values.run_root)


def _confidence_level(value: str) -> float:
    try:
        confidence_level = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("confidence level must be a number") from error
    if not 0.0 < confidence_level < 1.0:
        raise argparse.ArgumentTypeError("confidence level must be between zero and one")
    return confidence_level
