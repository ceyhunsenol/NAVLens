"""Executable composition root for TEFAS walk-forward backtests."""

import sys
from collections.abc import Sequence
from datetime import datetime

from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient, TefasSourceError

from .tefas_backtest import evaluate_tefas_acquisition
from .tefas_cli_arguments import parse_tefas_backtest_arguments
from .tefas_cli_output import format_tefas_backtest_result


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire TEFAS prices, run a baseline backtest, and return an exit code."""
    arguments = parse_tefas_backtest_arguments(argv)
    acquisition = AcquireTefasPrices(
        TefasHttpClient(),
        arguments.acquisition.raw_root,
    )
    try:
        acquired = acquisition.acquire(
            arguments.acquisition.request,
            arguments.acquisition.as_of,
            datetime.now().astimezone(),
        )
        result = evaluate_tefas_acquisition(acquired, arguments.estimator)
    except (TefasSourceError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(format_tefas_backtest_result(result))
    return 0
