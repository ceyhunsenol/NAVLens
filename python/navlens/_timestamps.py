"""Internal timestamp validation helpers for NAVLens."""

from datetime import datetime, timedelta

from navlens import UtcTimestamp


def validate_utc_timestamp(dt: datetime, field_name: str, error_cls: type[Exception]) -> None:
    """Validate that a value is a timezone-aware datetime in UTC."""
    if not isinstance(dt, datetime):
        raise error_cls(f"{field_name} must be a datetime instance")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise error_cls(f"{field_name} must include a timezone")
    if dt.utcoffset() != timedelta(0):
        raise error_cls(f"{field_name} must be in UTC timezone")


def datetime_to_utc_timestamp(
    dt: datetime, field_name: str, error_cls: type[Exception]
) -> UtcTimestamp:
    """Validate UTC timezone and zero microsecond precision, then convert to UtcTimestamp."""
    validate_utc_timestamp(dt, field_name, error_cls)
    if dt.microsecond != 0:
        raise error_cls(f"{field_name} must not contain fractional seconds (microseconds)")
    return UtcTimestamp(int(dt.timestamp()))
