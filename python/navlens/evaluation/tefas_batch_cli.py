"""Executable composition root for multi-fund TEFAS backtests."""

from collections.abc import Sequence

from navlens.sources.tefas import AcquireTefasPrices, TefasHttpClient

from .tefas_batch import batch_exit_code, run_tefas_batch
from .tefas_batch_arguments import TefasBatchCliArguments, parse_tefas_batch_arguments
from .tefas_batch_output import format_tefas_batch_result
from .tefas_execution import ExecuteTefasBacktest


def main(argv: Sequence[str] | None = None) -> int:
    """Run sequential per-fund backtests and report isolated failures."""
    arguments = parse_tefas_batch_arguments(argv)
    executor = _build_executor(arguments)
    result = run_tefas_batch(arguments.acquisitions, executor)
    print(format_tefas_batch_result(result))
    return batch_exit_code(result)


def _build_executor(arguments: TefasBatchCliArguments) -> ExecuteTefasBacktest:
    raw_root = arguments.acquisitions[0].raw_root
    return ExecuteTefasBacktest(
        AcquireTefasPrices(TefasHttpClient(), raw_root),
        arguments.estimator,
        arguments.run_root,
    )
