"""Chronological lag features built from canonical decimal returns."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

FEATURE_SCHEMA_VERSION = "lagged-returns-v1"
TARGET_NAME = "next_published_nav_return_decimal"


@dataclass(frozen=True)
class LaggedReturnDataset:
    """Training matrix whose rows only contain returns preceding each target."""

    features: pd.DataFrame
    targets: pd.Series
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    target_definition: str = TARGET_NAME


def build_lagged_return_dataset(
    returns: pd.Series,
    *,
    lookback: int,
) -> LaggedReturnDataset:
    """Build supervised rows without using the target or future observations."""
    clean_returns = _validated_returns(returns, minimum_size=lookback + 1, lookback=lookback)
    features = pd.DataFrame(
        {
            _feature_name(lag): clean_returns.shift(lag)
            for lag in range(1, lookback + 1)
        },
        index=clean_returns.index,
    ).dropna()
    targets = clean_returns.loc[features.index].rename(TARGET_NAME)
    return LaggedReturnDataset(features=features, targets=targets)


def build_latest_feature_row(returns: pd.Series, *, lookback: int) -> pd.DataFrame:
    """Build one inference row using only the most recently observed returns."""
    clean_returns = _validated_returns(returns, minimum_size=lookback, lookback=lookback)
    values = {
        _feature_name(lag): [clean_returns.iloc[-lag]]
        for lag in range(1, lookback + 1)
    }
    return pd.DataFrame(values, index=pd.DatetimeIndex([clean_returns.index[-1]]))


def _validated_returns(
    returns: pd.Series,
    *,
    minimum_size: int,
    lookback: int,
) -> pd.Series:
    if lookback < 1:
        raise ValueError("lookback must be at least one")
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


def _feature_name(lag: int) -> str:
    return f"return_decimal_lag_{lag}"
