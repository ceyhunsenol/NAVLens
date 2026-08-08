"""Dataset wrapper for historical FX-aware reconciliation outcomes."""

from dataclasses import dataclass

from .fx_outcome import HistoricalFxReconciliationOutcome


@dataclass(frozen=True, slots=True)
class HistoricalFxReconciliationDataset:
    """Immutable sequence of historical FX reconciliation outcomes mapped 1:1 with requests."""

    outcomes: tuple[HistoricalFxReconciliationOutcome, ...]
