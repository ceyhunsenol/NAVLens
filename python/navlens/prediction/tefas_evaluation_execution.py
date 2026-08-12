"""Reusable execution boundary for one stored TEFAS prediction."""

from dataclasses import dataclass
from datetime import date, datetime

from navlens import MarketDate
from navlens.sources.tefas import AcquireTefasPrices, TefasPriceRequest

from .artifact import SingleReturnPredictionArtifact
from .errors import PredictionArtifactError
from .live_evaluation import LivePredictionEvaluationResult, evaluate_tefas_prediction_artifact


@dataclass(frozen=True, slots=True)
class EvaluateTefasPredictionArtifact:
    """Load, acquire, and evaluate one versioned prediction artifact."""

    acquisition: AcquireTefasPrices
    as_of: date
    evaluated_at: datetime

    def evaluate(self, artifact: SingleReturnPredictionArtifact) -> LivePredictionEvaluationResult:
        """Acquire realized prices and evaluate one validated artifact."""
        validate_evaluation_as_of(artifact.target_date, self.as_of)
        request = _build_request(
            artifact.fund_id,
            artifact.last_observation_date,
            artifact.target_date,
        )
        acquired = self.acquisition.acquire(request, self.as_of, self.evaluated_at)
        return evaluate_tefas_prediction_artifact(
            artifact,
            acquired,
            evaluated_at=self.evaluated_at,
        )


def _build_request(
    fund_id: str,
    start_market_date: MarketDate,
    target_market_date: MarketDate,
) -> TefasPriceRequest:
    start_date = date.fromisoformat(str(start_market_date))
    end_date = date.fromisoformat(str(target_market_date))
    return TefasPriceRequest(fund_id, start_date, end_date)


def validate_evaluation_as_of(target_date: MarketDate, as_of: date) -> None:
    """Reject evaluation attempts before the target NAV can exist."""
    target = date.fromisoformat(str(target_date))
    if target > as_of:
        raise PredictionArtifactError(
            f"target date {target} is after evaluation as-of date {as_of}"
        )
