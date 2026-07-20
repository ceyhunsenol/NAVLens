"""Auditable records emitted by chronological model evaluation."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardRecord:
    """Scalar prediction record suitable for tables and visualisation."""

    prediction_date: pd.Timestamp
    target_date: pd.Timestamp
    predicted_return: float
    actual_return: float
    lower_bound: float
    upper_bound: float
    model_name: str
    model_version: str
    feature_schema_version: str
    training_start: pd.Timestamp
    training_end: pd.Timestamp
