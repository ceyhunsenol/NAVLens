"""Outcome records for historical reconciliation dataset construction."""

from dataclasses import dataclass

from navlens import MarketDate

from ..result import PointInTimeFundReturnReconciliationResult
from .request import HistoricalReconciliationRequest


@dataclass(frozen=True, slots=True)
class MissingHoldingsSkip:
    """Indicates the period was skipped because no holding snapshot was found."""


@dataclass(frozen=True, slots=True)
class MissingFundPriceSkip:
    """Indicates the period was skipped because a required fund price was missing."""

    required_date: MarketDate


HistoricalReconciliationSkipReason = MissingHoldingsSkip | MissingFundPriceSkip


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationRecord:
    """A successfully reconciled historical period."""

    request: HistoricalReconciliationRequest
    result: PointInTimeFundReturnReconciliationResult

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
class SkippedReconciliationRecord:
    """A period skipped due to a typed missing-data scenario."""

    request: HistoricalReconciliationRequest
    reason: HistoricalReconciliationSkipReason


HistoricalReconciliationOutcome = HistoricalReconciliationRecord | SkippedReconciliationRecord
