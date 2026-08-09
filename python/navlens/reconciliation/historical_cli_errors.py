"""Operational error handling policies for historical reconciliation CLIs."""

from navlens import NavlensValidationError
from navlens.alignment.errors import PointInTimeAlignmentError
from navlens.datasets import (
    FundUnitPriceDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from navlens.sources import (
    CsvFundUnitPriceSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
)

from .historical.errors import (
    HistoricalReconciliationDatasetError,
    InvalidHistoricalReconciliationRunConfigurationError,
)
from .historical.schedule_csv import CsvHistoricalScheduleSourceError

HISTORICAL_CLI_OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    InvalidHistoricalReconciliationRunConfigurationError,
    CsvHistoricalScheduleSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
    CsvFundUnitPriceSourceError,
    HistoricalReconciliationDatasetError,
    PointInTimeAlignmentError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
    FundUnitPriceDatasetError,
    NavlensValidationError,
    OSError,
)
