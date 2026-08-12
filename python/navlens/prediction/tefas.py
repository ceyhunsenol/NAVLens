"""Point-in-time prediction orchestration for acquired TEFAS prices."""

from datetime import datetime

from navlens import MarketDate
from navlens.sources.tefas import (
    TEFAS_SOURCE_ID,
    TefasAcquisitionResult,
    to_fund_unit_price_snapshots,
)

from .contracts import SingleReturnPredictionResult
from .errors import NoEligibleSnapshotsError
from .freshness import FundUnitPriceFreshnessPolicy
from .options import PredictionModelOptions
from .orchestration import predict_next_published_nav_return_from_snapshots


def predict_next_published_nav_return_from_tefas_acquisition(
    acquisition: TefasAcquisitionResult,
    *,
    acquired_at: datetime,
    prediction_date: MarketDate,
    target_date: MarketDate,
    model: PredictionModelOptions | None = None,
    freshness: FundUnitPriceFreshnessPolicy | None = None,
) -> SingleReturnPredictionResult:
    """Predict from one acquired TEFAS artifact through the canonical pipeline."""
    snapshots = to_fund_unit_price_snapshots(acquisition, acquired_at=acquired_at)
    if not snapshots:
        raise NoEligibleSnapshotsError("TEFAS acquisition contains no fund unit-price records")
    fund_ids = {snapshot.fund_id for snapshot in snapshots}
    if len(fund_ids) != 1:
        raise ValueError("TEFAS acquisition must contain records for exactly one fund")

    latest_market_date = max(snapshot.observation.date for snapshot in snapshots)
    selected_model = model or PredictionModelOptions()
    selected_freshness = freshness or FundUnitPriceFreshnessPolicy()
    selected_freshness.validate(prediction_date, latest_market_date)
    return predict_next_published_nav_return_from_snapshots(
        snapshots,
        fund_id=snapshots[0].fund_id,
        source_id=TEFAS_SOURCE_ID,
        prediction_timestamp=acquired_at,
        prediction_date=prediction_date,
        pricing_as_of_date=latest_market_date,
        target_date=target_date,
        lookback=selected_model.lookback,
        minimum_training_returns=selected_model.minimum_training_returns,
        confidence_level=selected_model.confidence_level,
        model_version=selected_model.model_version,
    )
