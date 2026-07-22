"""Internal timestamp validation helpers for research datasets."""

from datetime import datetime, timedelta


def validate_utc_timestamp(dt: datetime, field_name: str, error_cls: type[ValueError]) -> None:
    """Validate that a value is a timezone-aware datetime in UTC."""
    if not isinstance(dt, datetime):
        raise error_cls(f"{field_name} must be a datetime instance")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise error_cls(f"{field_name} must include a timezone")
    if dt.utcoffset() != timedelta(0):
        raise error_cls(f"{field_name} must be in UTC timezone")
