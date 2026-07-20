"""Mapping from an acquired TEFAS artifact into walk-forward evaluation."""

from dataclasses import dataclass

from navlens.datasets import FundReturnDataset, build_tefas_fund_returns
from navlens.sources.tefas import TefasAcquisitionResult

from .linear_baseline import LinearBaselineWalkForward
from .result import WalkForwardResult
from .walk_forward import run_walk_forward


@dataclass(frozen=True)
class TefasBacktestResult:
    """Source provenance, dataset, configuration, and evaluation result."""

    acquisition: TefasAcquisitionResult
    dataset: FundReturnDataset
    estimator: LinearBaselineWalkForward
    evaluation: WalkForwardResult


def evaluate_tefas_acquisition(
    acquisition: TefasAcquisitionResult,
    estimator: LinearBaselineWalkForward,
) -> TefasBacktestResult:
    """Evaluate one already-acquired artifact without performing I/O."""
    dataset = build_tefas_fund_returns(acquisition)
    evaluation = run_walk_forward(dataset.fund_id, dataset.returns, estimator)
    return TefasBacktestResult(acquisition, dataset, estimator, evaluation)
