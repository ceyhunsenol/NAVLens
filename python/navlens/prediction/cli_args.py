"""CLI argument parsing and validation for point-in-time return prediction."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from navlens import MarketDate


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
    parser.add_argument(
        "--lookback",
        type=_parse_positive_int,
        default=5,
        help="Number of lagged return features (default: 5).",
    )
    parser.add_argument(
        "--minimum-training-returns",
        type=_parse_positive_int,
        default=None,
        help="Minimum required historical returns for fitting (default: lookback + 3).",
    )
    parser.add_argument(
        "--confidence-level",
        type=_parse_confidence_level,
        default=0.90,
        help="Prediction interval confidence level in (0, 1) (default: 0.90).",
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default="v1",
        help="Model version string identifier (default: v1).",
    )
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
    if not args.model_version.strip():
        parser.error("--model-version cannot be empty")

    return PredictionCliArguments(
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        fund_id=args.fund_id.strip(),
        source_id=args.source_id.strip(),
        prediction_timestamp=args.prediction_timestamp,
        prediction_date=args.prediction_date,
        pricing_as_of_date=args.pricing_as_of_date,
        target_date=args.target_date,
        lookback=args.lookback,
        minimum_training_returns=args.minimum_training_returns,
        confidence_level=args.confidence_level,
        model_version=args.model_version.strip(),
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


def _parse_positive_int(val_str: str) -> int:
    try:
        val = int(val_str)
        if val < 1:
            raise ValueError
        return val
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"expected positive integer, got {val_str!r}") from err


def _parse_confidence_level(val_str: str) -> float:
    try:
        val = float(val_str)
        if not (0.0 < val < 1.0):
            raise ValueError
        return val
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            f"confidence level must be a float between 0 and 1, got {val_str!r}"
        ) from err
