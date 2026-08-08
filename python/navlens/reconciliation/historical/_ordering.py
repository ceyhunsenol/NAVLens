"""Chronological ordering validation for historical reconciliation datasets."""

from collections.abc import Iterable

from navlens import ReturnPeriod

from .errors import DecreasingPeriodError, DuplicatePeriodError


def validate_chronological_periods(periods: Iterable[ReturnPeriod]) -> None:
    """Validate that periods are strictly increasing without duplicate periods."""
    seen_periods: list[ReturnPeriod] = []
    prev_end = None
    for current_period in periods:
        current_end = current_period.period_end_date
        if any(current_period == seen_period for seen_period in seen_periods):
            raise DuplicatePeriodError(f"Duplicate period detected: {current_period}")
        if prev_end is not None and current_end <= prev_end:
            raise DecreasingPeriodError(
                f"Period end dates must be strictly increasing; got {current_end} after {prev_end}"
            )
        seen_periods.append(current_period)
        prev_end = current_end
