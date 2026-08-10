"""Provider-neutral CSV helper for point-in-time NAV return prediction."""

from datetime import datetime
from pathlib import Path

from navlens import MarketDate
from navlens.sources.fund_unit_prices_csv import read_fund_unit_prices_csv

from .contracts import SingleReturnPredictionResult
from .orchestration import predict_next_published_nav_return_from_snapshots


def predict_next_published_nav_return_from_csv(
    csv_path: str | Path,
    *,
    fund_id: str,
    source_id: str,
    prediction_timestamp: datetime,
    prediction_date: MarketDate,
    pricing_as_of_date: MarketDate,
    target_date: MarketDate,
    lookback: int = 5,
    minimum_training_returns: int | None = None,
    confidence_level: float = 0.90,
    model_version: str = "v1",
) -> SingleReturnPredictionResult:
    """Parse provider-neutral CSV snapshots and orchestrate a point-in-time prediction."""
    snapshots = read_fund_unit_prices_csv(csv_path)
    return predict_next_published_nav_return_from_snapshots(
        snapshots,
        fund_id=fund_id,
        source_id=source_id,
        prediction_timestamp=prediction_timestamp,
        prediction_date=prediction_date,
        pricing_as_of_date=pricing_as_of_date,
        target_date=target_date,
        lookback=lookback,
        minimum_training_returns=minimum_training_returns,
        confidence_level=confidence_level,
        model_version=model_version,
    )
