"""Model-independent expanding-window backtest orchestration."""

import pandas as pd

from navlens import BacktestObservation, MarketDate, evaluate_backtest
from navlens.datasets.return_series import validated_decimal_returns

from .contracts import FittedPrediction, WalkForwardEstimator
from .records import WalkForwardRecord
from .result import WalkForwardResult


def run_walk_forward(
    fund_id: str,
    returns: pd.Series,
    estimator: WalkForwardEstimator,
) -> WalkForwardResult:
    """Retrain chronologically and delegate all canonical metrics to Rust."""
    clean_returns = validated_decimal_returns(
        returns,
        minimum_size=estimator.initial_training_size + 1,
    )
    records: list[WalkForwardRecord] = []
    observations: list[BacktestObservation] = []

    for target_position in range(estimator.initial_training_size, len(clean_returns)):
        history = clean_returns.iloc[:target_position]
        target_date = pd.Timestamp(clean_returns.index[target_position])
        fitted = estimator.fit_predict(history)
        record, observation = _map_prediction(
            fitted,
            prediction_date=pd.Timestamp(history.index[-1]),
            target_date=target_date,
            actual_return=float(clean_returns.iloc[target_position]),
        )
        records.append(record)
        observations.append(observation)

    return WalkForwardResult(
        fund_id=fund_id,
        records=tuple(records),
        metrics=evaluate_backtest(fund_id, observations),
    )


def _map_prediction(
    fitted: FittedPrediction,
    *,
    prediction_date: pd.Timestamp,
    target_date: pd.Timestamp,
    actual_return: float,
) -> tuple[WalkForwardRecord, BacktestObservation]:
    prediction = fitted.prediction
    record = WalkForwardRecord(
        prediction_date=prediction_date,
        target_date=target_date,
        predicted_return=prediction.expected_return,
        actual_return=actual_return,
        lower_bound=prediction.lower_bound,
        upper_bound=prediction.upper_bound,
        model_name=prediction.model.name,
        model_version=prediction.model.version,
        feature_schema_version=prediction.model.feature_set_version,
        training_start=fitted.training_start,
        training_end=fitted.training_end,
    )
    observation = BacktestObservation(
        _market_date(prediction_date),
        _market_date(target_date),
        prediction,
        actual_return,
    )
    return record, observation


def _market_date(timestamp: pd.Timestamp) -> MarketDate:
    return MarketDate(timestamp.year, timestamp.month, timestamp.day)
