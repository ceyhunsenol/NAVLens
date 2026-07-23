"""Errors raised while constructing research datasets."""


class FundReturnDatasetError(ValueError):
    """Validated source values cannot form a research return dataset."""


class HoldingDatasetError(ValueError):
    """Validated holdings data cannot form a research dataset snapshot."""


class SecurityPriceDatasetError(ValueError):
    """Validated security price data cannot form a research dataset snapshot."""


class FundUnitPriceDatasetError(ValueError):
    """Validated fund unit-price data cannot form a research dataset snapshot."""
