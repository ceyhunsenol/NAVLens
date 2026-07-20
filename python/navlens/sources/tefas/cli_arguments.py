"""Command-line input mapping for TEFAS price acquisition."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .errors import TefasRequestError
from .request import TefasPriceRequest


@dataclass(frozen=True, slots=True)
class TefasCliArguments:
    """Validated provider request and local acquisition settings."""

    request: TefasPriceRequest
    as_of: date
    raw_root: Path


def parse_cli_arguments(
    argv: Sequence[str] | None = None, today: date | None = None
) -> TefasCliArguments:
    """Map command-line strings into explicit TEFAS acquisition types."""
    current_date = today or date.today()
    parser = _build_parser(current_date)
    values = parser.parse_args(argv)
    end_date = values.end_date or current_date
    days = values.days or 30
    start_date = values.start_date or end_date - timedelta(days=days - 1)
    try:
        request = TefasPriceRequest(values.fund_code, start_date, end_date)
        if end_date > values.as_of:
            raise TefasRequestError("end date must not be after the acquisition date")
    except TefasRequestError as error:
        parser.error(str(error))
    return TefasCliArguments(request, values.as_of, values.raw_root)


def _build_parser(today: date) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="navlens-fetch-tefas",
        description="Acquire one fund's dated TEFAS unit prices.",
    )
    parser.add_argument("fund_code", help="TEFAS fund code, for example AAL")
    interval = parser.add_mutually_exclusive_group()
    interval.add_argument("--start", dest="start_date", type=_iso_date)
    interval.add_argument("--days", type=_positive_days, metavar="N")
    parser.add_argument("--end", dest="end_date", type=_iso_date)
    parser.add_argument("--as-of", type=_iso_date, default=today)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/tefas"))
    return parser


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def _positive_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("days must be an integer") from error
    if days < 1:
        raise argparse.ArgumentTypeError("days must be positive")
    return days
