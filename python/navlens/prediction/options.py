"""Provider-neutral options for the implemented prediction baseline."""

from dataclasses import dataclass
from enum import StrEnum


class PredictionModelKind(StrEnum):
    """Implemented point-in-time return estimator choices."""

    LINEAR = "linear"
    HISTORICAL_MEAN = "historical-mean"
    LAST_RETURN = "last-return"


@dataclass(frozen=True, slots=True)
class PredictionModelOptions:
    """Group baseline settings passed to canonical prediction orchestration."""

    lookback: int = 5
    minimum_training_returns: int | None = None
    confidence_level: float = 0.90
    model_version: str = "v1"
    model_kind: PredictionModelKind = PredictionModelKind.LINEAR
