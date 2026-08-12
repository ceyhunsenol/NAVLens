"""Per-fund execution adapter for TEFAS prediction batches."""

from dataclasses import dataclass
from datetime import datetime

from navlens.sources.tefas import AcquireTefasPrices
from navlens.sources.tefas.cli_arguments import TefasCliArguments

from .contracts import SingleReturnPredictionResult
from .tefas import predict_next_published_nav_return_from_tefas_acquisition
from .tefas_cli_options import TefasPredictionCliOptions


@dataclass(frozen=True, slots=True)
class ExecuteTefasPrediction:
    """Acquire and predict one fund using shared batch settings."""

    acquisition: AcquireTefasPrices
    acquired_at: datetime
    options: TefasPredictionCliOptions

    def execute(self, arguments: TefasCliArguments) -> SingleReturnPredictionResult:
        acquired = self.acquisition.acquire(
            arguments.request,
            arguments.as_of,
            self.acquired_at,
        )
        return predict_next_published_nav_return_from_tefas_acquisition(
            acquired,
            acquired_at=self.acquired_at,
            prediction_date=self.options.prediction_date,
            target_date=self.options.target_date,
            model=self.options.model,
            freshness=self.options.freshness,
        )
