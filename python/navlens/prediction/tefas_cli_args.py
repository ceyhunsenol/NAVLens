"""CLI argument mapping for live TEFAS prediction."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from navlens import MarketDate
from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    build_tefas_cli_parser,
    tefas_cli_arguments_from_namespace,
)


@dataclass(frozen=True, slots=True)
class TefasPredictionCliArguments:
    """Validated acquisition and prediction settings."""

    acquisition: TefasCliArguments
    prediction_date: MarketDate
    target_date: MarketDate
    output_format: str


def parse_tefas_prediction_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionCliArguments:
    """Parse the keyless TEFAS prediction command."""
    current_date = today or date.today()
    parser = build_tefas_cli_parser(
        today=current_date,
        prog="navlens-predict-tefas",
        description="Acquire TEFAS prices and predict the next published NAV return.",
    )
    parser.add_argument("--target-date", type=_market_date, required=True)
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    values = parser.parse_args(argv)
    acquisition = tefas_cli_arguments_from_namespace(parser, values, current_date)
    prediction_date = _to_market_date(acquisition.as_of)
    if values.target_date <= prediction_date:
        parser.error("--target-date must be later than the prediction date")
    return TefasPredictionCliArguments(
        acquisition,
        prediction_date,
        values.target_date,
        values.output_format,
    )


def _market_date(value: str) -> MarketDate:
    try:
        return _to_market_date(date.fromisoformat(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def _to_market_date(value: date) -> MarketDate:
    return MarketDate(value.year, value.month, value.day)
