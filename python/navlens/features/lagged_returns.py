"""Chronological lag features built from canonical decimal returns."""

from dataclasses import dataclass

import pandas as pd

from navlens.datasets.return_series import validated_decimal_returns

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
    _validate_lookback(lookback)
    clean_returns = validated_decimal_returns(returns, minimum_size=lookback + 1)
    features = pd.DataFrame(
        {_feature_name(lag): clean_returns.shift(lag) for lag in range(1, lookback + 1)},
        index=clean_returns.index,
    ).dropna()
    targets = clean_returns.loc[features.index].rename(TARGET_NAME)
    return LaggedReturnDataset(features=features, targets=targets)


def build_latest_feature_row(returns: pd.Series, *, lookback: int) -> pd.DataFrame:
    """Build one inference row using only the most recently observed returns."""
    _validate_lookback(lookback)
    clean_returns = validated_decimal_returns(returns, minimum_size=lookback)
    values = {_feature_name(lag): [clean_returns.iloc[-lag]] for lag in range(1, lookback + 1)}
    return pd.DataFrame(values, index=pd.DatetimeIndex([clean_returns.index[-1]]))


def _validate_lookback(lookback: int) -> None:
    if lookback < 1:
        raise ValueError("lookback must be at least one")


def _feature_name(lag: int) -> str:
    return f"return_decimal_lag_{lag}"
