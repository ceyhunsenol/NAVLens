"""Shared prediction settings for single and batch TEFAS commands."""

import argparse
from dataclasses import dataclass
from datetime import date

from navlens import (
    MarketCalendar,
    MarketDate,
    NavlensValidationError,
    SessionKind,
    SessionOverride,
)

from .freshness import FundUnitPriceFreshnessPolicy
from .model_cli_options import (
    PredictionModelOptions,
    add_prediction_model_options,
    prediction_model_options_from_namespace,
)


@dataclass(frozen=True, slots=True)
class TefasPredictionCliOptions:
    """Validated prediction settings shared by TEFAS commands."""

    prediction_date: MarketDate
    target_date: MarketDate
    model: PredictionModelOptions
    freshness: FundUnitPriceFreshnessPolicy
    output_format: str


def add_tefas_prediction_options(parser: argparse.ArgumentParser) -> None:
    """Add target, model, freshness, and output options to a parser."""
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--target-date", type=_market_date)
    target.add_argument("--auto-target-date", action="store_true")
    parser.add_argument("--closed-date", type=_market_date, action="append", default=[])
    add_prediction_model_options(parser)
    parser.add_argument("--max-price-age-days", type=_non_negative_integer, default=4)
    parser.add_argument("--output-format", choices=["text", "json"], default="text")


def tefas_prediction_options_from_namespace(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
    prediction_day: date,
) -> TefasPredictionCliOptions:
    """Map parsed shared fields into validated prediction options."""
    prediction_date = _to_market_date(prediction_day)
    target_date = _resolve_target_date(parser, values, prediction_date)
    model = prediction_model_options_from_namespace(parser, values)
    freshness = FundUnitPriceFreshnessPolicy(values.max_price_age_days)
    return TefasPredictionCliOptions(
        prediction_date,
        target_date,
        model,
        freshness,
        values.output_format,
    )


def _resolve_target_date(
    parser: argparse.ArgumentParser,
    values: argparse.Namespace,
    prediction_date: MarketDate,
) -> MarketDate:
    if values.target_date is not None:
        if values.closed_date:
            parser.error("--closed-date requires --auto-target-date")
        if values.target_date <= prediction_date:
            parser.error("--target-date must be later than the prediction date")
        return values.target_date
    try:
        overrides = [
            SessionOverride(closed_date, SessionKind("closed"))
            for closed_date in values.closed_date
        ]
        return MarketCalendar(overrides).next_open_date(prediction_date)
    except NavlensValidationError as error:
        parser.error(str(error))


def _market_date(value: str) -> MarketDate:
    try:
        return _to_market_date(date.fromisoformat(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def _to_market_date(value: date) -> MarketDate:
    return MarketDate(value.year, value.month, value.day)


def _non_negative_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a non-negative integer") from error
    if number < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer")
    return number
