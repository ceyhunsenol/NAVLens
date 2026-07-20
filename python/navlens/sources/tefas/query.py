"""Provider-specific query mapping for TEFAS price history."""

from datetime import date

from .errors import TefasRequestError
from .request import TefasPriceRequest

SUPPORTED_PERIODS = (1, 3, 6, 12, 36, 60)


def build_price_query(request: TefasPriceRequest, as_of: date) -> dict[str, object]:
    """Map an explicit interval to the fixed look-back periods TEFAS accepts."""
    if request.end_date > as_of:
        raise TefasRequestError("end date must not be after the acquisition date")
    return {
        "fonKodu": request.normalized_fund_code,
        "dil": "TR",
        "periyod": _lookback_period(request.start_date, as_of),
    }


def _lookback_period(start_date: date, as_of: date) -> int:
    months = (as_of.year - start_date.year) * 12 + as_of.month - start_date.month
    months += start_date.day < as_of.day
    months = max(1, months)
    for period in SUPPORTED_PERIODS:
        if period >= months:
            return period
    raise TefasRequestError("TEFAS price history is limited to 60 months")
