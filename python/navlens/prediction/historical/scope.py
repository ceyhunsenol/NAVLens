"""Scope and provenance contracts for historical prediction evaluation."""

import math
from dataclasses import dataclass

from navlens.estimators.linear_baseline import LinearBaselineConfig

from .errors import InvalidHistoricalPredictionScopeError


@dataclass(frozen=True, slots=True)
class HistoricalPredictionEvaluationScope:
    """Provenance and dataset scope for historical prediction evaluation."""

    fund_id: str
    source_id: str
    lookback: int
    confidence_level: float
    model_version: str
    minimum_training_returns: int | None = None

    def __post_init__(self) -> None:
        """Validate scope invariants upon construction."""
        if not isinstance(self.fund_id, str) or not self.fund_id.strip():
            raise InvalidHistoricalPredictionScopeError(
                f"fund_id must be a non-empty string, got {self.fund_id!r}"
            )
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise InvalidHistoricalPredictionScopeError(
                f"source_id must be a non-empty string, got {self.source_id!r}"
            )
        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise InvalidHistoricalPredictionScopeError(
                f"model_version must be a non-empty string, got {self.model_version!r}"
            )
        if (
            isinstance(self.confidence_level, bool)
            or not isinstance(self.confidence_level, (int, float))
            or not math.isfinite(self.confidence_level)
            or not (0.0 < self.confidence_level < 1.0)
        ):
            raise InvalidHistoricalPredictionScopeError(
                "confidence_level must be a finite real number between 0 and 1 (exclusive), "
                f"got {self.confidence_level!r}"
            )

        try:
            LinearBaselineConfig(
                lookback=self.lookback,
                minimum_training_returns=self.minimum_training_returns,
            )
        except ValueError as err:
            raise InvalidHistoricalPredictionScopeError(str(err)) from err

    @property
    def resolved_minimum_training_returns(self) -> int:
        """The resolved minimum training returns required for fitting."""
        return LinearBaselineConfig(
            lookback=self.lookback,
            minimum_training_returns=self.minimum_training_returns,
        ).resolved_minimum_training_returns
