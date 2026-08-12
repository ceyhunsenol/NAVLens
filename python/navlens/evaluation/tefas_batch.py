"""Backtest compatibility exports for shared TEFAS batch orchestration."""

from navlens.sources.tefas.batch import (
    TefasBatchFailure,
    TefasBatchResult,
    TefasBatchSuccess,
    TefasExecutor,
    batch_exit_code,
    run_tefas_batch,
)

from .tefas_execution import CompletedTefasBacktest

BatchFundFailure = TefasBatchFailure
BatchFundSuccess = TefasBatchSuccess
TefasBacktestExecutor = TefasExecutor[CompletedTefasBacktest]

__all__ = [
    "BatchFundFailure",
    "BatchFundSuccess",
    "TefasBacktestExecutor",
    "TefasBatchResult",
    "batch_exit_code",
    "run_tefas_batch",
]
