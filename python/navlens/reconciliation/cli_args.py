"""Command-line argument parsing for point-in-time fund-return reconciliation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from navlens.alignment.return_contribution_cli_args import (
    ReturnContributionCliArguments,
    build_return_contribution_cli_parser,
    extract_return_contribution_arguments,
)


@dataclass(frozen=True, slots=True)
class ReconciliationCliArguments:
    """Parsed and validated command-line inputs for reconciliation CLI."""

    contribution_args: ReturnContributionCliArguments
    fund_unit_prices_csv: Path
    fund_price_source_id: str


def build_reconciliation_cli_parser() -> argparse.ArgumentParser:
    """Build parser for navlens-reconcile-fund-csv."""
    parser = build_return_contribution_cli_parser(
        prog="navlens-reconcile-fund-csv",
        description="Reconcile published fund return against observed portfolio contribution.",
    )
    parser.add_argument(
        "--fund-unit-prices-csv",
        required=True,
        type=Path,
        help="Path to CSV containing fund unit prices.",
    )
    parser.add_argument(
        "--fund-price-source-id",
        required=True,
        type=str,
        help="Source identifier for fund unit prices.",
    )
    return parser


def parse_reconciliation_cli_arguments(
    argv: Sequence[str] | None = None,
) -> ReconciliationCliArguments:
    """Parse raw CLI arguments into ReconciliationCliArguments."""
    parser = build_reconciliation_cli_parser()
    args = parser.parse_args(argv)

    contribution_args = extract_return_contribution_arguments(args)

    return ReconciliationCliArguments(
        contribution_args=contribution_args,
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        fund_price_source_id=args.fund_price_source_id,
    )
