"""Outcome records for historical FX-aware reconciliation dataset construction."""

from dataclasses import dataclass

from ..fx_result import PointInTimeFxFundReturnReconciliationResult
from .fx_request import HistoricalFxReconciliationRequest
from .outcome import HistoricalReconciliationSkipReason


@dataclass(frozen=True, slots=True)
class HistoricalFxReconciliationRecord:
    """A successfully reconciled historical FX-aware period."""

    request: HistoricalFxReconciliationRequest
    result: PointInTimeFxFundReturnReconciliationResult

    @property
    def published_fund_return(self) -> float:
        """The canonical published fund return (decimal) for the period."""
        return self.result.reconciliation_result.reconciliation.published_fund_return

    @property
    def return_coverage(self) -> float:
        """The coverage ratio of the observed portfolio contribution."""
        contrib = self.result.reconciliation_result.reconciliation.observed_portfolio_contribution
        return contrib.return_coverage

    @property
    def observed_portfolio_contribution(self) -> float:
        """The sum of all weighted asset decimal returns for the period."""
        contrib = self.result.reconciliation_result.reconciliation.observed_portfolio_contribution
        return contrib.observed_contribution

    @property
    def reconciliation_residual(self) -> float:
        """The raw difference between the published return and the covered contribution."""
        return self.result.reconciliation_result.reconciliation.reconciliation_residual


@dataclass(frozen=True, slots=True)
class SkippedFxReconciliationRecord:
    """An FX-aware period skipped due to a typed missing-data scenario."""

    request: HistoricalFxReconciliationRequest
    reason: HistoricalReconciliationSkipReason


HistoricalFxReconciliationOutcome = HistoricalFxReconciliationRecord | SkippedFxReconciliationRecord
