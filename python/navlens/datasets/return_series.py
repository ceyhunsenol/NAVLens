"""Validation for chronological decimal-return research series."""

import numpy as np
import pandas as pd


def validated_decimal_returns(returns: pd.Series, *, minimum_size: int) -> pd.Series:
    """Return a finite float series with a unique chronological date index."""
    if minimum_size < 1:
        raise ValueError("minimum_size must be at least one")
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise TypeError("returns must use a DatetimeIndex")
    if not returns.index.is_monotonic_increasing or not returns.index.is_unique:
        raise ValueError("returns must have a unique, chronological index")
    if len(returns) < minimum_size:
        raise ValueError(f"at least {minimum_size} returns are required")

    clean_returns = returns.astype(float)
    if not np.isfinite(clean_returns.to_numpy()).all():
        raise ValueError("returns must contain only finite values")
    return clean_returns
