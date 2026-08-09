"""Command-line argument parsing for historical reconciliation dataset evaluation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from navlens import CurrencyCode, PriceAdjustment

from .historical.schedule_csv import HistoricalReconciliationRunConfiguration


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationCliArguments:
    """Parsed and validated CLI inputs for historical reconciliation evaluation."""

    schedule_csv: Path
    holdings_csv: Path
    security_prices_csv: Path
    fund_unit_prices_csv: Path
    output_format: str
    config: HistoricalReconciliationRunConfiguration


def build_historical_reconciliation_cli_parser(
    prog: str = "navlens-evaluate-historical-reconciliation-csv",
    description: str = "Evaluate historical fund return reconciliation over multiple periods.",
) -> argparse.ArgumentParser:
    """Build argument parser for historical reconciliation CLI command."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--schedule-csv",
        required=True,
        type=Path,
        help="Path to CSV containing historical request schedule.",
    )
    parser.add_argument(
        "--holdings-csv",
        required=True,
        type=Path,
        help="Path to CSV containing holdings snapshots.",
    )
    parser.add_argument(
        "--security-prices-csv",
        required=True,
        type=Path,
        help="Path to CSV containing security prices.",
    )
    parser.add_argument(
        "--fund-unit-prices-csv",
        required=True,
        type=Path,
        help="Path to CSV containing fund unit prices.",
    )
    parser.add_argument(
        "--fund-id",
        required=True,
        type=str,
        help="Target fund identifier.",
    )
    parser.add_argument(
        "--holdings-source-id",
        required=True,
        type=str,
        help="Holdings source identifier.",
    )
    parser.add_argument(
        "--security-price-source-id",
        required=True,
        type=str,
        help="Security price source identifier.",
    )
    parser.add_argument(
        "--fund-price-source-id",
        required=True,
        type=str,
        help="Fund price source identifier.",
    )
    parser.add_argument(
        "--fund-base-currency",
        required=True,
        type=str,
        help="Fund base currency code (e.g. TRY).",
    )
    parser.add_argument(
        "--price-adjustment",
        required=True,
        type=str,
        help="Price adjustment variant (e.g. unadjusted).",
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
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output report format (default: text).",
    )
    return parser


def parse_historical_reconciliation_cli_arguments(
    argv: Sequence[str] | None = None,
) -> HistoricalReconciliationCliArguments:
    """Parse raw CLI arguments into HistoricalReconciliationCliArguments."""
    parser = build_historical_reconciliation_cli_parser()
    args = parser.parse_args(argv)

    config = HistoricalReconciliationRunConfiguration(
        fund_id=args.fund_id,
        holdings_source_id=args.holdings_source_id,
        security_price_source_id=args.security_price_source_id,
        fund_price_source_id=args.fund_price_source_id,
        fund_base_currency=CurrencyCode(args.fund_base_currency),
        required_price_adjustment=PriceAdjustment(args.price_adjustment),
        minimum_observations=args.minimum_observations,
        max_staleness_calendar_days=args.max_staleness_calendar_days,
    )

    return HistoricalReconciliationCliArguments(
        schedule_csv=args.schedule_csv,
        holdings_csv=args.holdings_csv,
        security_prices_csv=args.security_prices_csv,
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        output_format=args.output_format,
        config=config,
    )
