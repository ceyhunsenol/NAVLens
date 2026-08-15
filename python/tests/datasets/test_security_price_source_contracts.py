"""Tests for provider-neutral security price source contracts and error hierarchy."""

from datetime import date, datetime

import pytest
from navlens.datasets import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceQueryError,
    SecurityPriceSourceError,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)


def test_valid_security_price_query() -> None:
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 22))
    assert query.instrument_id == "TRY_GARAN"
    assert query.normalized_instrument_id == "TRY_GARAN"
    assert query.start_date == date(2026, 7, 20)
    assert query.end_date == date(2026, 7, 22)


def test_query_trims_instrument_id() -> None:
    query = SecurityPriceQuery("  TRY_GARAN  ", date(2026, 7, 20), date(2026, 7, 20))
    assert query.normalized_instrument_id == "TRY_GARAN"


@pytest.mark.parametrize("invalid_id", ["", "   ", None, 123])
def test_query_rejects_invalid_instrument_id(invalid_id: object) -> None:
    with pytest.raises(SecurityPriceQueryError, match="instrument_id"):
        SecurityPriceQuery(invalid_id, date(2026, 7, 20), date(2026, 7, 22))  # type: ignore[arg-type]


def test_query_rejects_datetime_instances() -> None:
    dt = datetime(2026, 7, 20, 12, 0)
    with pytest.raises(SecurityPriceQueryError, match="start_date"):
        SecurityPriceQuery("TRY_GARAN", dt, date(2026, 7, 22))  # type: ignore[arg-type]
    with pytest.raises(SecurityPriceQueryError, match="end_date"):
        SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), dt)  # type: ignore[arg-type]


def test_query_rejects_inverted_dates() -> None:
    with pytest.raises(SecurityPriceQueryError, match="on or before"):
        SecurityPriceQuery("TRY_GARAN", date(2026, 7, 25), date(2026, 7, 20))


def test_query_is_frozen() -> None:
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 22))
    with pytest.raises(AttributeError):
        query.instrument_id = "OTHER"  # type: ignore[misc]


def test_error_hierarchy_single_inheritance() -> None:
    assert issubclass(SecurityPriceQueryError, ValueError)
    assert not issubclass(SecurityPriceQueryError, RuntimeError)

    assert issubclass(SecurityPriceSourceError, RuntimeError)
    assert issubclass(SecurityPriceUnmappedInstrumentError, SecurityPriceSourceError)
    assert issubclass(SecurityPriceSourceUnavailableError, SecurityPriceSourceError)
    assert issubclass(SecurityPriceCorruptedSourceDataError, SecurityPriceSourceError)

    # Verify distinct single-inheritance subtyping
    assert not issubclass(SecurityPriceUnmappedInstrumentError, KeyError)
    assert not issubclass(
        SecurityPriceSourceUnavailableError, SecurityPriceCorruptedSourceDataError
    )
    assert not issubclass(
        SecurityPriceCorruptedSourceDataError, SecurityPriceSourceUnavailableError
    )
