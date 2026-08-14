"""Per-fund execution adapter for TEFAS prediction model-suite batches."""

from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate
from navlens.sources.tefas import AcquireTefasPrices
from navlens.sources.tefas.cli_arguments import TefasCliArguments

from .freshness import FundUnitPriceFreshnessPolicy
from .model_suite import (
    PredictionModelSuiteOptions,
    PredictionModelSuiteResult,
    predict_tefas_model_suite,
)


@dataclass(frozen=True, slots=True)
class ExecuteTefasPredictionSuite:
    """Acquire and predict all baselines for one fund using shared batch settings."""

    acquisition: AcquireTefasPrices
    acquired_at: datetime
    prediction_date: MarketDate
    target_date: MarketDate
    suite_options: PredictionModelSuiteOptions
    freshness: FundUnitPriceFreshnessPolicy

    def execute(self, arguments: TefasCliArguments) -> PredictionModelSuiteResult:
        """Acquire fund prices once and run every model baseline."""
        acquired = self.acquisition.acquire(
            arguments.request,
            arguments.as_of,
            self.acquired_at,
        )
        return predict_tefas_model_suite(
            acquired,
            acquired_at=self.acquired_at,
            prediction_date=self.prediction_date,
            target_date=self.target_date,
            options=self.suite_options,
            freshness=self.freshness,
        )
