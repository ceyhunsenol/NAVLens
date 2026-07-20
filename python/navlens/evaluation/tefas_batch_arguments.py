"""Command-line mapping for sequential multi-fund TEFAS backtests."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    add_tefas_acquisition_arguments,
    tefas_cli_arguments_for_fund,
)

from .backtest_cli_options import (
    add_backtest_cli_options,
    backtest_cli_options_from_namespace,
)
from .linear_baseline import LinearBaselineWalkForward


@dataclass(frozen=True, slots=True)
class TefasBatchCliArguments:
    """Validated requests and shared settings for one batch."""

    acquisitions: tuple[TefasCliArguments, ...]
    estimator: LinearBaselineWalkForward
    run_root: Path


def parse_tefas_batch_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasBatchCliArguments:
    """Map a multi-fund command into explicit per-fund requests."""
    current_date = today or date.today()
    parser = argparse.ArgumentParser(
        prog="navlens-backtest-batch",
        description="Run sequential TEFAS backtests for multiple funds.",
    )
    parser.add_argument("fund_codes", nargs="+", help="TEFAS fund codes")
    add_tefas_acquisition_arguments(parser, current_date)
    add_backtest_cli_options(parser)
    values = parser.parse_args(argv)
    acquisitions = tuple(
        tefas_cli_arguments_for_fund(parser, values, current_date, fund_code)
        for fund_code in values.fund_codes
    )
    _reject_duplicate_funds(parser, acquisitions)
    options = backtest_cli_options_from_namespace(parser, values)
    return TefasBatchCliArguments(acquisitions, options.estimator, options.run_root)


def _reject_duplicate_funds(
    parser: argparse.ArgumentParser,
    acquisitions: tuple[TefasCliArguments, ...],
) -> None:
    normalized = [item.request.normalized_fund_code for item in acquisitions]
    if len(set(normalized)) != len(normalized):
        parser.error("fund codes must be unique")
