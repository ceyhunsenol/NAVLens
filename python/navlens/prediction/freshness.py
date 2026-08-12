"""Explicit fund unit-price freshness policy for prediction inputs."""

from dataclasses import dataclass

from navlens import MarketDate

from .errors import (
    InvalidPredictionConfigurationError,
    InvalidPredictionWindowError,
    StaleFundUnitPriceHistoryError,
)


@dataclass(frozen=True, slots=True)
class FundUnitPriceFreshnessPolicy:
    """Bound acceptable observation age in calendar days."""

    maximum_age_calendar_days: int = 4

    def __post_init__(self) -> None:
        value = self.maximum_age_calendar_days
        if type(value) is not int or value < 0:
            raise InvalidPredictionConfigurationError(
                "maximum fund unit-price age must be a non-negative integer"
            )

    def validate(self, prediction_date: MarketDate, latest_date: MarketDate) -> int:
        """Return native-computed age or reject future/stale observations."""
        age = prediction_date.calendar_days_since(latest_date)
        if age < 0:
            raise InvalidPredictionWindowError(
                f"latest fund unit-price date ({latest_date}) is after prediction date "
                f"({prediction_date})"
            )
        if age > self.maximum_age_calendar_days:
            raise StaleFundUnitPriceHistoryError(
                f"latest fund unit price is {age} calendar days old; configured maximum is "
                f"{self.maximum_age_calendar_days} ({latest_date} to {prediction_date})"
            )
        return age
