"""Operational error policy for the historical prediction CLI."""

from navlens import NavlensValidationError
from navlens.datasets import FundUnitPriceDatasetError
from navlens.sources import CsvFundUnitPriceSourceError

from .errors import PointInTimePredictionError
from .historical.errors import HistoricalPredictionDatasetError
from .historical.schedule_csv import CsvHistoricalPredictionScheduleSourceError

HISTORICAL_PREDICTION_CLI_OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    CsvHistoricalPredictionScheduleSourceError,
    CsvFundUnitPriceSourceError,
    HistoricalPredictionDatasetError,
    PointInTimePredictionError,
    FundUnitPriceDatasetError,
    NavlensValidationError,
    OSError,
)
