"""Provider-neutral point-in-time return prediction orchestration."""

from collections.abc import Iterable
from datetime import datetime

from navlens import MarketDate, PredictionRequest, calculate_price_returns
from navlens._timestamps import datetime_to_utc_timestamp, validate_utc_timestamp
from navlens.datasets import select_fund_unit_price_snapshots
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot
from navlens.datasets.pandas_returns import dated_returns_to_series

from .contracts import SingleReturnPredictionResult
from .errors import (
    InsufficientVisibleHistoryError,
    InvalidPredictionConfigurationError,
    InvalidPredictionWindowError,
    NoEligibleSnapshotsError,
    PointInTimePredictionError,
)
from .model_execution import fit_prediction_model, resolve_required_training_returns
from .options import PredictionModelKind

TARGET_DEFINITION = "next_published_nav_return_decimal"


def predict_next_published_nav_return_from_snapshots(
    snapshots: Iterable[FundUnitPriceSnapshot],
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
    model_kind: PredictionModelKind = PredictionModelKind.LINEAR,
) -> SingleReturnPredictionResult:
    """Orchestrate a provider-neutral point-in-time next published NAV return prediction."""
    validate_utc_timestamp(prediction_timestamp, "prediction_timestamp", PointInTimePredictionError)

    if pricing_as_of_date > prediction_date:
        raise InvalidPredictionWindowError(
            f"pricing_as_of_date ({pricing_as_of_date}) cannot be later than "
            f"prediction_date ({prediction_date})"
        )
    if prediction_date >= target_date:
        raise InvalidPredictionWindowError(
            f"prediction_date ({prediction_date}) must precede target_date ({target_date})"
        )

    try:
        required_training_returns = resolve_required_training_returns(
            model_kind,
            lookback,
            minimum_training_returns,
        )
    except ValueError as error:
        raise InvalidPredictionConfigurationError(str(error)) from error

    selected = select_fund_unit_price_snapshots(
        snapshots,
        source_id=source_id,
        fund_id=fund_id,
        at_timestamp=prediction_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )
    if not selected:
        raise NoEligibleSnapshotsError(
            f"no price snapshots found for fund '{fund_id}' from source '{source_id}' "
            f"available on or before {prediction_timestamp.isoformat()} "
            f"with market_date <= {pricing_as_of_date}"
        )

    last_observation_date = selected[-1].observation.date
    if last_observation_date > prediction_date:
        raise InvalidPredictionWindowError(
            f"last observation date ({last_observation_date}) cannot be later than "
            f"prediction_date ({prediction_date})"
        )

    required_snapshot_count = required_training_returns + 1
    if len(selected) < required_snapshot_count:
        raise InsufficientVisibleHistoryError(
            f"selected snapshot count ({len(selected)}) is less than required minimum "
            f"({required_snapshot_count}) for resolved training returns threshold "
            f"({required_training_returns})"
        )

    observations = [snapshot.observation for snapshot in selected]
    dated_returns = calculate_price_returns(fund_id, observations)
    if len(dated_returns) != len(selected) - 1:
        raise RuntimeError(
            f"Internal invariant failure: expected {len(selected) - 1} native dated returns, "
            f"got {len(dated_returns)}"
        )

    returns = dated_returns_to_series(dated_returns)

    model_fit = fit_prediction_model(
        returns,
        model_kind=model_kind,
        lookback=lookback,
        minimum_training_returns=minimum_training_returns,
        model_version=model_version,
        confidence_level=confidence_level,
    )
    fitted = model_fit.fitted

    actual_data_as_of = max(snapshot.available_at for snapshot in selected)

    generated_at_ts = datetime_to_utc_timestamp(
        prediction_timestamp, "prediction_timestamp", PointInTimePredictionError
    )
    data_as_of_ts = datetime_to_utc_timestamp(
        actual_data_as_of, "actual_data_as_of", PointInTimePredictionError
    )

    request = PredictionRequest(
        fund_id,
        prediction_date,
        target_date,
        generated_at_ts,
        data_as_of_ts,
    )

    training_target_start_date = MarketDate(
        fitted.training_start.year,
        fitted.training_start.month,
        fitted.training_start.day,
    )
    training_target_end_date = MarketDate(
        fitted.training_end.year,
        fitted.training_end.month,
        fitted.training_end.day,
    )

    return SingleReturnPredictionResult(
        request=request,
        prediction=fitted.prediction,
        source_id=source_id,
        prediction_timestamp=prediction_timestamp,
        pricing_as_of_date=pricing_as_of_date,
        selected_snapshots=tuple(selected),
        training_return_count=len(dated_returns),
        training_target_start_date=training_target_start_date,
        training_target_end_date=training_target_end_date,
        lookback=model_fit.effective_lookback,
        target_definition=TARGET_DEFINITION,
    )
