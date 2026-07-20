"""Reusable execution boundary for one complete TEFAS backtest run."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from navlens.sources.tefas import TefasAcquisitionResult
from navlens.sources.tefas.cli_arguments import TefasCliArguments
from navlens.sources.tefas.request import TefasPriceRequest

from .linear_baseline import LinearBaselineWalkForward
from .manifests import StoredRunManifest, build_tefas_run_manifest, store_run_manifest
from .tefas_backtest import TefasBacktestResult, evaluate_tefas_acquisition


class TefasPriceAcquisition(Protocol):
    """Provider acquisition capability consumed by one backtest execution."""

    def acquire(
        self,
        request: TefasPriceRequest,
        as_of: date,
        acquired_at: datetime,
    ) -> TefasAcquisitionResult: ...


@dataclass(frozen=True, slots=True)
class CompletedTefasBacktest:
    """Evaluation result paired with its persisted evidence artifact."""

    result: TefasBacktestResult
    manifest: StoredRunManifest


class ExecuteTefasBacktest:
    """Acquire, evaluate, and persist one fund through existing boundaries."""

    def __init__(
        self,
        acquisition: TefasPriceAcquisition,
        estimator: LinearBaselineWalkForward,
        run_root: str | Path,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._acquisition = acquisition
        self._estimator = estimator
        self._run_root = run_root
        self._clock = clock or _local_now

    def execute(self, arguments: TefasCliArguments) -> CompletedTefasBacktest:
        """Run one configured fund without handling transport-level errors."""
        acquired = self._acquisition.acquire(
            arguments.request,
            arguments.as_of,
            self._clock(),
        )
        result = evaluate_tefas_acquisition(acquired, self._estimator)
        manifest = build_tefas_run_manifest(
            result,
            arguments.request,
            arguments.as_of,
            self._clock(),
        )
        stored = store_run_manifest(manifest, self._run_root)
        return CompletedTefasBacktest(result, stored)


def _local_now() -> datetime:
    return datetime.now().astimezone()
