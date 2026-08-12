"""Shared sequential execution boundary for multi-fund TEFAS operations."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from .cli_arguments import TefasCliArguments
from .errors import TefasSourceError

T = TypeVar("T")


class TefasExecutor(Protocol[T]):
    """One typed per-fund operation consumed by TEFAS batch orchestration."""

    def execute(self, arguments: TefasCliArguments) -> T: ...


@dataclass(frozen=True, slots=True)
class TefasBatchSuccess(Generic[T]):
    """One requested fund and its completed operation."""

    fund_code: str
    completed: T


@dataclass(frozen=True, slots=True)
class TefasBatchFailure:
    """One expected per-fund failure that did not stop the batch."""

    fund_code: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class TefasBatchResult(Generic[T]):
    """Categorized successes and failures from one sequential batch."""

    successes: tuple[TefasBatchSuccess[T], ...]
    failures: tuple[TefasBatchFailure, ...]

    @property
    def total(self) -> int:
        return len(self.successes) + len(self.failures)


def run_tefas_batch(
    acquisitions: tuple[TefasCliArguments, ...],
    executor: TefasExecutor[T],
) -> TefasBatchResult[T]:
    """Execute funds in input order while isolating expected boundary errors."""
    if not acquisitions:
        raise ValueError("batch requires at least one fund")
    successes: list[TefasBatchSuccess[T]] = []
    failures: list[TefasBatchFailure] = []
    for arguments in acquisitions:
        fund_code = arguments.request.normalized_fund_code
        try:
            completed = executor.execute(arguments)
        except (OSError, TefasSourceError, ValueError) as error:
            failures.append(TefasBatchFailure(fund_code, type(error).__name__, str(error)))
        else:
            successes.append(TefasBatchSuccess(fund_code, completed))
    return TefasBatchResult(tuple(successes), tuple(failures))


def batch_exit_code(result: TefasBatchResult[T]) -> int:
    """Return zero for success, two for partial success, or one for failure."""
    if not result.failures:
        return 0
    return 2 if result.successes else 1
