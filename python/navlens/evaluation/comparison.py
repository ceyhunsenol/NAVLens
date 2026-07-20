"""Fair comparison of estimators over identical walk-forward targets."""

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from .contracts import WalkForwardEstimator
from .result import WalkForwardResult
from .walk_forward import run_walk_forward


@dataclass(frozen=True)
class ModelComparisonEntry:
    """One identified estimator result within a fair comparison."""

    model_name: str
    model_version: str
    result: WalkForwardResult


@dataclass(frozen=True)
class ModelComparisonResult:
    """Estimator results evaluated on an identical target-date sequence."""

    fund_id: str
    entries: tuple[ModelComparisonEntry, ...]


def compare_walk_forward(
    fund_id: str,
    returns: pd.Series,
    estimators: Sequence[WalkForwardEstimator],
) -> ModelComparisonResult:
    """Evaluate estimators only when their initial windows are identical."""
    if not estimators:
        raise ValueError("at least one estimator is required")
    initial_sizes = {estimator.initial_training_size for estimator in estimators}
    if len(initial_sizes) != 1:
        raise ValueError("compared estimators must use the same initial training size")

    entries = tuple(
        _entry(run_walk_forward(fund_id, returns, estimator)) for estimator in estimators
    )
    _validate_entries(entries)
    return ModelComparisonResult(fund_id, entries)


def _entry(result: WalkForwardResult) -> ModelComparisonEntry:
    first_record = result.records[0]
    return ModelComparisonEntry(
        model_name=first_record.model_name,
        model_version=first_record.model_version,
        result=result,
    )


def _validate_entries(entries: tuple[ModelComparisonEntry, ...]) -> None:
    model_names = {entry.model_name for entry in entries}
    if len(model_names) != len(entries):
        raise ValueError("compared estimators must have unique model names")
    target_dates = {
        tuple(record.target_date for record in entry.result.records) for entry in entries
    }
    if len(target_dates) != 1:
        raise ValueError("compared estimators must use identical target dates")
