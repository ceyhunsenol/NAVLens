"""Dataset wrapper for historical reconciliation outcomes."""

from dataclasses import dataclass

from .outcome import HistoricalReconciliationOutcome


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationDataset:
    """Immutable sequence of historical reconciliation outcomes mapped 1:1 with requests."""

    outcomes: tuple[HistoricalReconciliationOutcome, ...]
