"""Fixtures and helper builders for historical prediction tests."""

from datetime import UTC, date, datetime, timedelta

from navlens import MarketDate, PeriodDecimalReturn, PriceObservation, ReturnPeriod, UnitPrice
from navlens.datasets import FundUnitPriceSnapshot
from navlens.prediction import (
    SingleReturnPredictionResult,
    predict_next_published_nav_return_from_snapshots,
)
from navlens.prediction.historical import (
    HistoricalPredictionEvaluationScope,
    HistoricalPredictionRequest,
)


def make_snapshot(
    fund_id: str = "FUND_A",
    source_id: str = "SOURCE_1",
    market_date: date = date(2026, 1, 1),
    price: float = 100.0,
    available_at: datetime | None = None,
) -> FundUnitPriceSnapshot:
    """Construct a real FundUnitPriceSnapshot domain object."""
    if available_at is None:
        available_at = datetime(2026, 1, 1, 18, 0, tzinfo=UTC)
    obs = PriceObservation(
        MarketDate(market_date.year, market_date.month, market_date.day),
        UnitPrice(price),
    )
    return FundUnitPriceSnapshot(
        fund_id=fund_id,
        observation=obs,
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def sample_snapshots(
    fund_id: str = "FUND_A",
    source_id: str = "SOURCE_1",
    count: int = 15,
    base_date: date = date(2026, 1, 1),
    start_time: datetime | None = None,
) -> list[FundUnitPriceSnapshot]:
    """Construct a sequence of price snapshots for fitting models."""
    if start_time is None:
        start_time = datetime(2026, 1, 1, 18, 0, tzinfo=UTC)
    snapshots = []
    current_price = 100.0
    for i in range(count):
        m_date = base_date + timedelta(days=i)
        avail = start_time + timedelta(days=i)
        current_price *= 1.002
        snapshots.append(
            make_snapshot(
                fund_id=fund_id,
                source_id=source_id,
                market_date=m_date,
                price=current_price,
                available_at=avail,
            )
        )
    return snapshots


def make_scope(
    fund_id: str = "FUND_A",
    source_id: str = "SOURCE_1",
    lookback: int = 5,
    confidence_level: float = 0.95,
    model_version: str = "v1.0",
    minimum_training_returns: int | None = None,
) -> HistoricalPredictionEvaluationScope:
    """Construct a test HistoricalPredictionEvaluationScope."""
    return HistoricalPredictionEvaluationScope(
        fund_id=fund_id,
        source_id=source_id,
        lookback=lookback,
        confidence_level=confidence_level,
        model_version=model_version,
        minimum_training_returns=minimum_training_returns,
    )


def make_request(
    prediction_date: MarketDate | None = None,
    pricing_as_of_date: MarketDate | None = None,
    target_date: MarketDate | None = None,
    prediction_timestamp: datetime | None = None,
    evaluation_timestamp: datetime | None = None,
) -> HistoricalPredictionRequest:
    """Construct a test HistoricalPredictionRequest."""
    if prediction_date is None:
        prediction_date = MarketDate(2026, 1, 10)
    if pricing_as_of_date is None:
        pricing_as_of_date = prediction_date
    if target_date is None:
        d = date.fromisoformat(str(prediction_date))
        target_d = d + timedelta(days=1)
        target_date = MarketDate(target_d.year, target_d.month, target_d.day)
    if prediction_timestamp is None:
        prediction_timestamp = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    if evaluation_timestamp is None:
        evaluation_timestamp = datetime(2026, 1, 11, 18, 0, tzinfo=UTC)

    return HistoricalPredictionRequest(
        prediction_date=prediction_date,
        pricing_as_of_date=pricing_as_of_date,
        target_date=target_date,
        prediction_timestamp=prediction_timestamp,
        evaluation_timestamp=evaluation_timestamp,
    )


def make_prediction_result(
    snapshots: list[FundUnitPriceSnapshot] | None = None,
    fund_id: str = "FUND_A",
    source_id: str = "SOURCE_1",
    prediction_date: MarketDate | None = None,
    pricing_as_of_date: MarketDate | None = None,
    target_date: MarketDate | None = None,
    prediction_timestamp: datetime | None = None,
    lookback: int = 5,
    confidence_level: float = 0.95,
    model_version: str = "v1.0",
) -> SingleReturnPredictionResult:
    """Produce a real SingleReturnPredictionResult via orchestration."""
    if prediction_date is None:
        prediction_date = MarketDate(2026, 1, 10)
    if pricing_as_of_date is None:
        pricing_as_of_date = prediction_date
    if target_date is None:
        d = date.fromisoformat(str(prediction_date))
        target_d = d + timedelta(days=1)
        target_date = MarketDate(target_d.year, target_d.month, target_d.day)
    if prediction_timestamp is None:
        prediction_timestamp = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)

    if snapshots is None:
        snapshots = sample_snapshots(fund_id=fund_id, source_id=source_id, count=12)
    return predict_next_published_nav_return_from_snapshots(
        snapshots,
        fund_id=fund_id,
        source_id=source_id,
        prediction_date=prediction_date,
        pricing_as_of_date=pricing_as_of_date,
        target_date=target_date,
        prediction_timestamp=prediction_timestamp,
        lookback=lookback,
        confidence_level=confidence_level,
        model_version=model_version,
    )


def make_period_return(
    start_date: MarketDate | None = None,
    end_date: MarketDate | None = None,
    return_decimal: float = 0.002,
) -> PeriodDecimalReturn:
    """Construct a real PeriodDecimalReturn PyO3 domain object."""
    if start_date is None:
        start_date = MarketDate(2026, 1, 10)
    if end_date is None:
        end_date = MarketDate(2026, 1, 11)
    period = ReturnPeriod(start_date, end_date)
    return PeriodDecimalReturn(period, return_decimal)
