"""Errors raised while constructing research datasets."""


class FundReturnDatasetError(ValueError):
    """Validated source values cannot form a research return dataset."""


class HoldingDatasetError(ValueError):
    """Validated holdings data cannot form a research dataset snapshot."""
