"""Parsing of TEFAS price-history JSON payloads."""

from collections.abc import Mapping
from datetime import date

from .errors import TefasPayloadError
from .records import TefasPriceRecord
from .request import TefasPriceRequest


def parse_price_records(
    payload: Mapping[str, object], request: TefasPriceRequest
) -> list[TefasPriceRecord]:
    """Parse and interval-filter provider rows without financial validation."""
    error_code = payload.get("errorCode")
    if error_code is not None:
        message = payload.get("errorMessage") or "provider returned an error"
        raise TefasPayloadError(f"TEFAS error {error_code}: {message}")
    raw_rows = payload.get("resultList")
    if not isinstance(raw_rows, list):
        raise TefasPayloadError("TEFAS payload is missing resultList")

    records = [_parse_row(row, index, request) for index, row in enumerate(raw_rows)]
    return [
        record for record in records if request.start_date <= record.market_date <= request.end_date
    ]


def _parse_row(raw_row: object, index: int, request: TefasPriceRequest) -> TefasPriceRecord:
    if not isinstance(raw_row, Mapping):
        raise _row_error(index, "row must be an object")
    try:
        market_date = date.fromisoformat(str(raw_row["tarih"]))
        fund_code = str(raw_row["fonKodu"]).strip().upper()
        unit_price = float(raw_row["fiyat"])
    except (KeyError, TypeError, ValueError) as error:
        raise _row_error(index, "invalid tarih, fonKodu, or fiyat") from error
    if fund_code != request.normalized_fund_code:
        raise _row_error(index, f"unexpected fund code {fund_code!r}")
    return TefasPriceRecord(market_date, fund_code, unit_price)


def _row_error(index: int, message: str) -> TefasPayloadError:
    return TefasPayloadError(f"TEFAS resultList[{index}]: {message}")
