"""Point-in-time initial availability policy for TCMB daily rates."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from navlens import MarketCalendar, MarketDate, SessionKind

TCMB_AVAILABILITY_POLICY_ID: str = "tcmb_daily_rates_scheduled_publication"
TCMB_AVAILABILITY_POLICY_VERSION: str = "1"


def initial_tcmb_available_at(
    market_date: MarketDate,
    calendar: MarketCalendar,
) -> datetime | None:
    if calendar.session_on(market_date) != SessionKind("full_day"):
        return None

    dt_date = date.fromisoformat(str(market_date))
    local_dt = datetime.combine(dt_date, time(15, 30), tzinfo=ZoneInfo("Europe/Istanbul"))
    return local_dt.astimezone(UTC)
