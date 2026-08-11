"""Public dataset builder for provider-neutral point-in-time historical predictions."""

from collections.abc import Iterable

from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot

from ._period import evaluate_historical_prediction_period
from ._schedule import validate_historical_prediction_schedule
from .dataset import HistoricalPredictionDataset
from .outcome import HistoricalPredictionOutcome
from .request import HistoricalPredictionRequest
from .scope import HistoricalPredictionEvaluationScope


def build_historical_prediction_dataset(
    scope: HistoricalPredictionEvaluationScope,
    requests: Iterable[HistoricalPredictionRequest],
    snapshots: Iterable[FundUnitPriceSnapshot],
) -> HistoricalPredictionDataset:
    """Build a provider-neutral point-in-time historical prediction dataset."""
    requests_tuple = tuple(requests)
    validate_historical_prediction_schedule(requests_tuple)

    materialized_snapshots = tuple(snapshots)

    outcomes: list[HistoricalPredictionOutcome] = [
        evaluate_historical_prediction_period(request, scope, materialized_snapshots)
        for request in requests_tuple
    ]

    return HistoricalPredictionDataset(scope=scope, outcomes=tuple(outcomes))
