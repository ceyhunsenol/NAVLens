"""Typed persistence records for versioned backtest run artifacts."""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SCHEMA_VERSION = "navlens-backtest-run-v1"
TARGET_DEFINITION = "next_published_nav_return_decimal"


@dataclass(frozen=True, slots=True)
class SourceArtifactManifest:
    """Provenance of the immutable source bytes evaluated by a run."""

    provider: str
    path: str
    sha256: str
    from_cache: bool
    acquisition_as_of: date
    requested_start_date: date
    requested_end_date: date
    source_record_count: int


@dataclass(frozen=True, slots=True)
class RunConfigurationManifest:
    """Shared comparison configuration and linear-model specialization."""

    initial_training_returns: int
    confidence_level: float
    linear_lookback: int


@dataclass(frozen=True, slots=True)
class MetricsManifest:
    """Canonical Rust-produced metrics serialized without recalculation."""

    sample_count: int
    mean_absolute_error_decimal: float
    mean_error_decimal: float
    root_mean_squared_error_decimal: float
    direction_accuracy: float
    interval_coverage: float | None
    interval_mean_width_decimal: float | None


@dataclass(frozen=True, slots=True)
class PredictionManifest:
    """One dated decimal-return prediction and its observed target."""

    prediction_date: date
    target_date: date
    predicted_return_decimal: float
    actual_return_decimal: float
    lower_bound_decimal: float
    upper_bound_decimal: float
    training_start: date
    training_end: date


@dataclass(frozen=True, slots=True)
class ModelRunManifest:
    """Model identity, canonical metrics, and chronological predictions."""

    model_name: str
    model_version: str
    feature_schema_version: str
    metrics: MetricsManifest
    predictions: tuple[PredictionManifest, ...]


@dataclass(frozen=True, slots=True)
class BacktestRunManifest:
    """Complete versioned evidence for one model-comparison run."""

    schema_version: str
    run_id: str
    generated_at: datetime
    fund_id: str
    target_definition: str
    configuration: RunConfigurationManifest
    source: SourceArtifactManifest
    models: tuple[ModelRunManifest, ...]


@dataclass(frozen=True, slots=True)
class StoredRunManifest:
    """Identity and location returned by the local manifest store."""

    run_id: str
    path: Path
