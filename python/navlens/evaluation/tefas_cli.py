"""Executable composition root for TEFAS walk-forward backtests."""

import sys
from collections.abc import Sequence

from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient, TefasSourceError

from .tefas_cli_arguments import parse_tefas_backtest_arguments
from .tefas_cli_output import format_tefas_backtest_result
from .tefas_execution import ExecuteTefasBacktest


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire TEFAS prices, run a baseline backtest, and return an exit code."""
    arguments = parse_tefas_backtest_arguments(argv)
    executor = ExecuteTefasBacktest(
        AcquireTefasPrices(TefasHttpClient(), arguments.acquisition.raw_root),
        arguments.estimator,
        arguments.run_root,
    )
    try:
        completed = executor.execute(arguments.acquisition)
    except (OSError, TefasSourceError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(format_tefas_backtest_result(completed.result, completed.manifest))
    return 0
