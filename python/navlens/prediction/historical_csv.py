"""CSV orchestration for point-in-time historical prediction evaluation."""

from navlens.sources import read_fund_unit_prices_csv

from .historical import (
    HistoricalPredictionEvaluation,
    build_historical_prediction_dataset,
    evaluate_historical_prediction_dataset,
    read_historical_prediction_requests_csv,
)
from .historical_cli_args import HistoricalPredictionCliArguments


def evaluate_historical_prediction_from_csv(
    arguments: HistoricalPredictionCliArguments,
) -> HistoricalPredictionEvaluation:
    """Read inputs, build the historical prediction dataset, and evaluate it."""
    if not isinstance(arguments, HistoricalPredictionCliArguments):
        target_type = type(arguments).__name__
        raise TypeError(
            f"arguments must be a HistoricalPredictionCliArguments instance, got {target_type}"
        )

    requests = read_historical_prediction_requests_csv(arguments.schedule_csv)
    snapshots = read_fund_unit_prices_csv(arguments.fund_unit_prices_csv)
    dataset = build_historical_prediction_dataset(arguments.scope, requests, snapshots)
    return evaluate_historical_prediction_dataset(dataset)
