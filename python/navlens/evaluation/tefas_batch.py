"""Sequential batch orchestration with per-fund failure isolation."""

from dataclasses import dataclass
from typing import Protocol

from navlens.sources.tefas import TefasSourceError
from navlens.sources.tefas.cli_arguments import TefasCliArguments

from .tefas_execution import CompletedTefasBacktest


class TefasBacktestExecutor(Protocol):
    """Single-fund operation consumed by batch orchestration."""

    def execute(self, arguments: TefasCliArguments) -> CompletedTefasBacktest: ...


@dataclass(frozen=True, slots=True)
class BatchFundSuccess:
    """One requested fund and its completed backtest."""

    fund_code: str
    completed: CompletedTefasBacktest


@dataclass(frozen=True, slots=True)
class BatchFundFailure:
    """One expected per-fund failure that did not stop the batch."""

    fund_code: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class TefasBatchResult:
    """Categorized successes and failures from one sequential batch."""

    successes: tuple[BatchFundSuccess, ...]
    failures: tuple[BatchFundFailure, ...]

    @property
    def total(self) -> int:
        return len(self.successes) + len(self.failures)


def run_tefas_batch(
    acquisitions: tuple[TefasCliArguments, ...],
    executor: TefasBacktestExecutor,
) -> TefasBatchResult:
    """Execute funds in input order while isolating expected boundary errors."""
    if not acquisitions:
        raise ValueError("batch requires at least one fund")
    successes: list[BatchFundSuccess] = []
    failures: list[BatchFundFailure] = []
    for arguments in acquisitions:
        fund_code = arguments.request.normalized_fund_code
        try:
            completed = executor.execute(arguments)
        except (OSError, TefasSourceError, ValueError) as error:
            failures.append(BatchFundFailure(fund_code, type(error).__name__, str(error)))
        else:
            successes.append(BatchFundSuccess(fund_code, completed))
    return TefasBatchResult(tuple(successes), tuple(failures))


def batch_exit_code(result: TefasBatchResult) -> int:
    """Return zero for success, two for partial success, or one for failure."""
    if not result.failures:
        return 0
    return 2 if result.successes else 1
