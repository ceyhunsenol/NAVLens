"""Mapping from an acquired TEFAS artifact into walk-forward evaluation."""

from dataclasses import dataclass

from navlens.datasets import FundReturnDataset, build_tefas_fund_returns
from navlens.sources.tefas import TefasAcquisitionResult

from .comparison import ModelComparisonResult, compare_walk_forward
from .historical_mean import HistoricalMeanBaseline
from .last_return import LastReturnBaseline
from .linear_baseline import LinearBaselineWalkForward
from .result import WalkForwardResult


@dataclass(frozen=True)
class TefasBacktestResult:
    """Source provenance, dataset, configuration, and evaluation result."""

    acquisition: TefasAcquisitionResult
    dataset: FundReturnDataset
    estimator: LinearBaselineWalkForward
    evaluation: WalkForwardResult
    comparison: ModelComparisonResult


def evaluate_tefas_acquisition(
    acquisition: TefasAcquisitionResult,
    estimator: LinearBaselineWalkForward,
) -> TefasBacktestResult:
    """Evaluate one already-acquired artifact without performing I/O."""
    dataset = build_tefas_fund_returns(acquisition)
    comparison = compare_walk_forward(
        dataset.fund_id,
        dataset.returns,
        _comparison_estimators(estimator),
    )
    evaluation = comparison.entries[0].result
    return TefasBacktestResult(
        acquisition,
        dataset,
        estimator,
        evaluation,
        comparison,
    )


def _comparison_estimators(
    estimator: LinearBaselineWalkForward,
) -> tuple[LinearBaselineWalkForward, HistoricalMeanBaseline, LastReturnBaseline]:
    common = {
        "initial_training_size": estimator.initial_training_size,
        "model_version": estimator.model_version,
        "confidence_level": estimator.confidence_level,
    }
    return (
        estimator,
        HistoricalMeanBaseline(**common),
        LastReturnBaseline(**common),
    )
