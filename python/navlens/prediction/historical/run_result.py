"""Auditable result contract for one historical prediction run."""

from dataclasses import dataclass

from .dataset import HistoricalPredictionDataset
from .errors import InvalidHistoricalPredictionRunResultError
from .evaluation import HistoricalPredictionEvaluation
from .outcome import HistoricalPredictionRecord, SkippedPredictionRecord


@dataclass(frozen=True, slots=True)
class HistoricalPredictionRunResult:
    """Retain ordered period outcomes alongside their aggregate native evaluation."""

    dataset: HistoricalPredictionDataset
    evaluation: HistoricalPredictionEvaluation

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, HistoricalPredictionDataset):
            raise InvalidHistoricalPredictionRunResultError(
                "dataset must be a HistoricalPredictionDataset instance"
            )
        if not isinstance(self.evaluation, HistoricalPredictionEvaluation):
            raise InvalidHistoricalPredictionRunResultError(
                "evaluation must be a HistoricalPredictionEvaluation instance"
            )

        evaluated = sum(
            isinstance(item, HistoricalPredictionRecord) for item in self.dataset.outcomes
        )
        skipped = sum(isinstance(item, SkippedPredictionRecord) for item in self.dataset.outcomes)
        if self.evaluation.total_period_count != len(self.dataset.outcomes):
            raise InvalidHistoricalPredictionRunResultError(
                "evaluation total_period_count does not match dataset outcomes"
            )
        if self.evaluation.evaluated_period_count != evaluated:
            raise InvalidHistoricalPredictionRunResultError(
                "evaluation evaluated_period_count does not match dataset outcomes"
            )
        if self.evaluation.skipped_period_count != skipped:
            raise InvalidHistoricalPredictionRunResultError(
                "evaluation skipped_period_count does not match dataset outcomes"
            )

        expected_scope = self.dataset.scope if self.dataset.outcomes else None
        if self.evaluation.scope != expected_scope:
            raise InvalidHistoricalPredictionRunResultError(
                "evaluation scope does not match dataset scope"
            )
