"""Provider-neutral options for the implemented prediction baseline."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PredictionModelOptions:
    """Group baseline settings passed to canonical prediction orchestration."""

    lookback: int = 5
    minimum_training_returns: int | None = None
    confidence_level: float = 0.90
    model_version: str = "v1"
