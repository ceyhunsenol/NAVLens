import pytest
from navlens import (
    MarketCalendar,
    MarketDate,
    NavlensValidationError,
    SessionKind,
    SessionOverride,
)


def test_session_kind_variants_and_properties() -> None:
    full = SessionKind("full_day")
    half = SessionKind("half_day")
    closed = SessionKind("closed")

    assert full.name == "full_day"
    assert full.is_open() is True
    assert str(full) == "full_day"
    assert repr(full) == "SessionKind('full_day')"

    assert half.name == "half_day"
    assert half.is_open() is True
    assert str(half) == "half_day"
    assert repr(half) == "SessionKind('half_day')"

    assert closed.name == "closed"
    assert closed.is_open() is False
    assert str(closed) == "closed"
    assert repr(closed) == "SessionKind('closed')"

    assert full == SessionKind("FULL_DAY")
    assert half == SessionKind("HALF_DAY")
    assert closed == SessionKind("CLOSED")


def test_session_kind_rejects_unknown_kind() -> None:
    with pytest.raises(NavlensValidationError, match="unknown session kind"):
        SessionKind("unknown_kind")


def test_session_override_construction_and_getters() -> None:
    date = MarketDate(2026, 1, 15)
    kind = SessionKind("half_day")
    override = SessionOverride(date, kind)

    assert isinstance(override.date, MarketDate)
    assert isinstance(override.session, SessionKind)
    assert override.date == date
    assert override.session == kind


def test_default_market_calendar_weekday_and_weekend_behavior() -> None:
    cal = MarketCalendar()

    monday = MarketDate(2026, 1, 12)
    monday_session = cal.session_on(monday)
    assert isinstance(monday_session, SessionKind)
    assert monday_session == SessionKind("full_day")
    assert monday_session.is_open() is True

    saturday = MarketDate(2026, 1, 17)
    saturday_session = cal.session_on(saturday)
    assert isinstance(saturday_session, SessionKind)
    assert saturday_session == SessionKind("closed")
    assert saturday_session.is_open() is False


def test_explicit_closed_override_changes_weekday_behavior() -> None:
    monday = MarketDate(2026, 1, 12)
    override = SessionOverride(monday, SessionKind("closed"))
    cal = MarketCalendar([override])

    session = cal.session_on(monday)
    assert session == SessionKind("closed")
    assert session.is_open() is False


def test_explicit_half_day_override_preserved() -> None:
    tuesday = MarketDate(2026, 1, 13)
    override = SessionOverride(tuesday, SessionKind("half_day"))
    cal = MarketCalendar([override])

    session = cal.session_on(tuesday)
    assert session == SessionKind("half_day")
    assert session.is_open() is True


def test_duplicate_session_override_date_raises_validation_error() -> None:
    date = MarketDate(2026, 1, 15)
    override1 = SessionOverride(date, SessionKind("half_day"))
    override2 = SessionOverride(date, SessionKind("closed"))

    with pytest.raises(NavlensValidationError, match="duplicate session override"):
        MarketCalendar([override1, override2])


def test_next_open_date_behavior() -> None:
    friday = MarketDate(2026, 1, 16)
    cal = MarketCalendar()

    next_date = cal.next_open_date(friday)
    assert isinstance(next_date, MarketDate)
    assert next_date == MarketDate(2026, 1, 19)

    monday_holiday = SessionOverride(MarketDate(2026, 1, 19), SessionKind("closed"))
    cal_with_holiday = MarketCalendar([monday_holiday])

    next_date_holiday = cal_with_holiday.next_open_date(friday)
    assert next_date_holiday == MarketDate(2026, 1, 20)
