"""Command-line input mapping for TEFAS walk-forward backtests."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    build_tefas_cli_parser,
    tefas_cli_arguments_from_namespace,
)

from .backtest_cli_options import (
    add_backtest_cli_options,
    backtest_cli_options_from_namespace,
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
    add_backtest_cli_options(parser)
    values = parser.parse_args(argv)
    acquisition = tefas_cli_arguments_from_namespace(parser, values, current_date)
    options = backtest_cli_options_from_namespace(parser, values)
    return TefasBacktestCliArguments(acquisition, options.estimator, options.run_root)
