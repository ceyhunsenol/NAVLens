"""CLI argument parsing and validation for point-in-time return prediction."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from navlens import MarketDate

from .model_cli_options import (
    add_prediction_model_options,
    prediction_model_options_from_namespace,
)


@dataclass(frozen=True, slots=True)
class PredictionCliArguments:
    """Validated command-line arguments for point-in-time fund prediction."""

    fund_unit_prices_csv: Path
    fund_id: str
    source_id: str
    prediction_timestamp: datetime
    prediction_date: MarketDate
    pricing_as_of_date: MarketDate
    target_date: MarketDate
    lookback: int
    minimum_training_returns: int | None
    confidence_level: float
    model_version: str
    output_format: str


def parse_prediction_cli_arguments(
    argv: Sequence[str] | None = None,
) -> PredictionCliArguments:
    """Parse and validate command-line arguments for navlens-predict-fund-csv."""
    parser = argparse.ArgumentParser(
        prog="navlens-predict-fund-csv",
        description="Predict fund next published NAV return from point-in-time snapshots.",
    )

    parser.add_argument(
        "--fund-unit-prices-csv",
        type=Path,
        required=True,
        help="Path to provider-neutral CSV file containing fund unit-price snapshots.",
    )
    parser.add_argument(
        "--fund-id",
        type=str,
        required=True,
        help="Fund identifier string (e.g. AAL).",
    )
    parser.add_argument(
        "--source-id",
        type=str,
        required=True,
        help="Price source identifier string (e.g. tefas).",
    )
    parser.add_argument(
        "--prediction-timestamp",
        type=_parse_utc_datetime,
        required=True,
        help="ISO 8601 UTC timestamp cutoff for snapshot availability (e.g. 2026-07-28T00:00:00Z).",
    )
    parser.add_argument(
        "--prediction-date",
        type=_parse_market_date,
        required=True,
        help="ISO 8601 prediction MarketDate (e.g. 2026-07-27).",
    )
    parser.add_argument(
        "--pricing-as-of-date",
        type=_parse_market_date,
        required=True,
        help="ISO 8601 pricing as-of cutoff MarketDate (e.g. 2026-07-27).",
    )
    parser.add_argument(
        "--target-date",
        type=_parse_market_date,
        required=True,
        help="ISO 8601 target MarketDate for predicted return (e.g. 2026-07-28).",
    )
    add_prediction_model_options(parser)
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output serialization format (default: text).",
    )

    args = parser.parse_args(argv)

    if not args.fund_id.strip():
        parser.error("--fund-id cannot be empty")
    if not args.source_id.strip():
        parser.error("--source-id cannot be empty")
    model = prediction_model_options_from_namespace(parser, args)

    return PredictionCliArguments(
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        fund_id=args.fund_id.strip(),
        source_id=args.source_id.strip(),
        prediction_timestamp=args.prediction_timestamp,
        prediction_date=args.prediction_date,
        pricing_as_of_date=args.pricing_as_of_date,
        target_date=args.target_date,
        lookback=model.lookback,
        minimum_training_returns=model.minimum_training_returns,
        confidence_level=model.confidence_level,
        model_version=model.model_version,
        output_format=args.output_format,
    )


def _parse_market_date(val_str: str) -> MarketDate:
    try:
        parsed = date.fromisoformat(val_str)
        return MarketDate(parsed.year, parsed.month, parsed.day)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid ISO date {val_str!r}") from err


def _parse_utc_datetime(val_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        if dt.utcoffset() != UTC.utcoffset(dt):
            raise ValueError("timestamp must be in UTC timezone")
        return dt
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid ISO UTC timestamp {val_str!r}: {err}") from err
