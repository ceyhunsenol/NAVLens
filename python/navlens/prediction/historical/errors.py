"""Boundary exceptions for historical prediction datasets and evaluation."""


class HistoricalPredictionDatasetError(Exception):
    """Base exception for historical prediction dataset errors."""


class InvalidHistoricalPredictionScopeError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction evaluation scope violates contract invariants."""


class InvalidHistoricalPredictionRequestError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction request violates contract invariants."""
