from datetime import UTC, datetime

from navlens import MarketCalendar, MarketDate, SessionKind, SessionOverride
from navlens.sources.tcmb import (
    TCMB_AVAILABILITY_POLICY_ID,
    TCMB_AVAILABILITY_POLICY_VERSION,
    initial_tcmb_available_at,
)


def test_tcmb_availability_policy_constants() -> None:
    assert isinstance(TCMB_AVAILABILITY_POLICY_ID, str)
    assert len(TCMB_AVAILABILITY_POLICY_ID) > 0
    assert TCMB_AVAILABILITY_POLICY_ID == "tcmb_daily_rates_scheduled_publication"

    assert isinstance(TCMB_AVAILABILITY_POLICY_VERSION, str)
    assert len(TCMB_AVAILABILITY_POLICY_VERSION) > 0
    assert TCMB_AVAILABILITY_POLICY_VERSION == "1"


def test_normal_full_day_returns_timezone_aware_utc_timestamp() -> None:
    cal = MarketCalendar()
    market_date = MarketDate(2026, 1, 15)

    available_at = initial_tcmb_available_at(market_date, cal)

    assert available_at is not None
    assert isinstance(available_at, datetime)
    assert available_at.tzinfo == UTC
    assert available_at == datetime(2026, 1, 15, 12, 30, 0, tzinfo=UTC)


def test_historical_europe_istanbul_conversion_not_fixed_offset() -> None:
    cal = MarketCalendar()

    winter_date = MarketDate(2015, 1, 15)
    winter_available_at = initial_tcmb_available_at(winter_date, cal)
    assert winter_available_at == datetime(2015, 1, 15, 13, 30, 0, tzinfo=UTC)

    summer_date = MarketDate(2015, 7, 15)
    summer_available_at = initial_tcmb_available_at(summer_date, cal)
    assert summer_available_at == datetime(2015, 7, 15, 12, 30, 0, tzinfo=UTC)


def test_default_weekend_returns_none() -> None:
    cal = MarketCalendar()

    saturday = MarketDate(2026, 1, 17)
    sunday = MarketDate(2026, 1, 18)

    assert initial_tcmb_available_at(saturday, cal) is None
    assert initial_tcmb_available_at(sunday, cal) is None


def test_explicit_closed_weekday_override_returns_none() -> None:
    monday = MarketDate(2026, 1, 12)
    cal = MarketCalendar([SessionOverride(monday, SessionKind("closed"))])

    assert initial_tcmb_available_at(monday, cal) is None


def test_explicit_half_day_override_returns_none() -> None:
    tuesday = MarketDate(2026, 1, 13)
    cal = MarketCalendar([SessionOverride(tuesday, SessionKind("half_day"))])

    assert initial_tcmb_available_at(tuesday, cal) is None


def test_explicit_full_day_override_returns_timestamp() -> None:
    saturday = MarketDate(2026, 1, 17)
    cal = MarketCalendar([SessionOverride(saturday, SessionKind("full_day"))])

    available_at = initial_tcmb_available_at(saturday, cal)

    assert available_at == datetime(2026, 1, 17, 12, 30, 0, tzinfo=UTC)
