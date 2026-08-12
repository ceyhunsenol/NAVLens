import pytest
from navlens import MarketDate
from navlens.prediction import (
    FundUnitPriceFreshnessPolicy,
    InvalidPredictionConfigurationError,
    InvalidPredictionWindowError,
    StaleFundUnitPriceHistoryError,
)


def test_accepts_age_at_inclusive_boundary() -> None:
    policy = FundUnitPriceFreshnessPolicy(4)

    assert policy.validate(MarketDate(2026, 8, 12), MarketDate(2026, 8, 8)) == 4


def test_rejects_age_beyond_boundary_with_context() -> None:
    policy = FundUnitPriceFreshnessPolicy(3)

    with pytest.raises(StaleFundUnitPriceHistoryError, match="4 calendar days old"):
        policy.validate(MarketDate(2026, 8, 12), MarketDate(2026, 8, 8))


@pytest.mark.parametrize("value", [-1, True, 1.5, "4"])
def test_rejects_invalid_policy_values(value: object) -> None:
    with pytest.raises(InvalidPredictionConfigurationError):
        FundUnitPriceFreshnessPolicy(value)  # type: ignore[arg-type]


def test_rejects_observation_after_prediction_date() -> None:
    policy = FundUnitPriceFreshnessPolicy()

    with pytest.raises(InvalidPredictionWindowError, match="after prediction date"):
        policy.validate(MarketDate(2026, 8, 11), MarketDate(2026, 8, 12))
