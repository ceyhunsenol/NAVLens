"""Command-line argument parsing for point-in-time holdings/price alignment."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from navlens import AlignmentPolicy, CurrencyCode, MarketDate, PriceAdjustment
from navlens.datasets._timestamps import validate_utc_timestamp

from .request import PointInTimeAlignmentRequest


@dataclass(frozen=True, slots=True)
class AlignmentCliArguments:
    """Parsed and validated command-line inputs for alignment CLI."""

    holdings_csv: Path
    security_prices_csv: Path
    request: PointInTimeAlignmentRequest


def parse_market_date(val: str) -> MarketDate:
    parsed = date.fromisoformat(val)
    return MarketDate(parsed.year, parsed.month, parsed.day)


def _parse_utc_datetime(val: str) -> datetime:
    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    validate_utc_timestamp(dt, "prediction_timestamp", ValueError)
    return dt


def build_alignment_cli_parser(
    prog: str = "navlens-align-holdings-csv",
    description: str = "Run point-in-time holdings and security-price alignment on CSV files.",
) -> argparse.ArgumentParser:
    """Build parser for alignment-related CLI commands."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )
    parser.add_argument("--holdings-csv", required=True, type=Path, help="Path to holdings CSV.")
    parser.add_argument(
        "--security-prices-csv", required=True, type=Path, help="Path to security prices CSV."
    )
    parser.add_argument("--fund-id", required=True, type=str, help="Target fund identifier.")
    parser.add_argument(
        "--holdings-source-id", required=True, type=str, help="Holdings source identifier."
    )
    parser.add_argument(
        "--security-price-source-id",
        required=True,
        type=str,
        help="Security price source identifier.",
    )
    parser.add_argument(
        "--prediction-timestamp",
        required=True,
        type=str,
        help="Timezone-aware UTC ISO-8601 prediction timestamp.",
    )
    parser.add_argument(
        "--pricing-as-of-date",
        required=True,
        type=str,
        help="Pricing as-of date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--fund-base-currency", required=True, type=str, help="Fund base currency code (e.g. TRY)."
    )
    parser.add_argument(
        "--price-adjustment",
        required=True,
        type=str,
        help="Price adjustment variant (e.g. total_return_adjusted).",
    )
    parser.add_argument(
        "--minimum-observations",
        required=True,
        type=int,
        help="Minimum required observations per series.",
    )
    parser.add_argument(
        "--max-staleness-calendar-days",
        required=True,
        type=int,
        help="Maximum allowed price staleness in calendar days.",
    )
    return parser


def extract_alignment_arguments(args: argparse.Namespace) -> AlignmentCliArguments:
    """Extract AlignmentCliArguments from parsed argparse.Namespace."""
    pricing_as_of = parse_market_date(args.pricing_as_of_date)
    prediction_ts = _parse_utc_datetime(args.prediction_timestamp)

    policy = AlignmentPolicy(
        fund_base_currency=CurrencyCode(args.fund_base_currency),
        required_price_adjustment=PriceAdjustment(args.price_adjustment),
        pricing_as_of_date=pricing_as_of,
        minimum_observations=args.minimum_observations,
        max_staleness_calendar_days=args.max_staleness_calendar_days,
    )

    request = PointInTimeAlignmentRequest(
        fund_id=args.fund_id,
        prediction_timestamp=prediction_ts,
        holdings_source_id=args.holdings_source_id,
        security_price_source_id=args.security_price_source_id,
        policy=policy,
    )

    return AlignmentCliArguments(
        holdings_csv=args.holdings_csv,
        security_prices_csv=args.security_prices_csv,
        request=request,
    )


def parse_alignment_cli_arguments(
    argv: Sequence[str] | None = None,
) -> AlignmentCliArguments:
    """Parse raw CLI arguments into AlignmentCliArguments."""
    parser = build_alignment_cli_parser()
    args = parser.parse_args(argv)
    return extract_alignment_arguments(args)
