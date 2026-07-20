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
    parser = build_tefas_cli_parser(
        today=current_date,
        prog="navlens-fetch-tefas",
        description="Acquire one fund's dated TEFAS unit prices.",
    )
    values = parser.parse_args(argv)
    return tefas_cli_arguments_from_namespace(parser, values, current_date)


def tefas_cli_arguments_from_namespace(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
    today: date,
) -> TefasCliArguments:
    """Map shared TEFAS CLI fields parsed by a composition-root command."""
    return tefas_cli_arguments_for_fund(parser, values, today, values.fund_code)


def tefas_cli_arguments_for_fund(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
    today: date,
    fund_code: str,
) -> TefasCliArguments:
    """Map shared parsed fields for one explicit fund code."""
    end_date = values.end_date or today
    days = values.days or 30
    start_date = values.start_date or end_date - timedelta(days=days - 1)
    try:
        request = TefasPriceRequest(fund_code, start_date, end_date)
        if end_date > values.as_of:
            raise TefasRequestError("end date must not be after the acquisition date")
    except TefasRequestError as error:
        parser.error(str(error))
    return TefasCliArguments(request, values.as_of, values.raw_root)


def build_tefas_cli_parser(
    *,
    today: date,
    prog: str,
    description: str,
) -> argparse.ArgumentParser:
    """Create a command parser containing the shared TEFAS acquisition fields."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )
    parser.add_argument("fund_code", help="TEFAS fund code, for example AAL")
    add_tefas_acquisition_arguments(parser, today)
    return parser


def add_tefas_acquisition_arguments(
    parser: argparse.ArgumentParser,
    today: date,
) -> None:
    """Add provider interval and local-source options to a parser."""
    interval = parser.add_mutually_exclusive_group()
    interval.add_argument("--start", dest="start_date", type=_iso_date)
    interval.add_argument("--days", type=positive_integer, metavar="N")
    parser.add_argument("--end", dest="end_date", type=_iso_date)
    parser.add_argument("--as-of", type=_iso_date, default=today)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/tefas"))


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def positive_integer(value: str) -> int:
    """Parse one strictly positive command-line integer."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("value must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return number
