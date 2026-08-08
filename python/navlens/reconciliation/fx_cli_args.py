"""Command-line argument parsing for FX-adjusted point-in-time fund-return reconciliation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from navlens.alignment.fx_return_contribution_cli_args import (
    FxReturnContributionCliArguments,
    build_fx_return_contribution_cli_parser,
    extract_fx_return_contribution_arguments,
)


@dataclass(frozen=True, slots=True)
class FxReconciliationCliArguments:
    """Parsed and validated command-line inputs for FX reconciliation CLI."""

    fx_contribution_args: FxReturnContributionCliArguments
    fund_unit_prices_csv: Path
    fund_price_source_id: str


def build_fx_reconciliation_cli_parser() -> argparse.ArgumentParser:
    """Build parser for navlens-fx-reconcile-fund-csv."""
    parser = build_fx_return_contribution_cli_parser(
        prog="navlens-fx-reconcile-fund-csv",
        description=(
            "Reconcile published fund return against observed FX-adjusted portfolio contribution."
        ),
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


def extract_fx_reconciliation_arguments(
    args: argparse.Namespace,
) -> FxReconciliationCliArguments:
    """Extract FxReconciliationCliArguments from a parsed namespace."""
    fx_contrib_args = extract_fx_return_contribution_arguments(args)
    return FxReconciliationCliArguments(
        fx_contribution_args=fx_contrib_args,
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        fund_price_source_id=args.fund_price_source_id,
    )


def parse_fx_reconciliation_cli_arguments(
    argv: Sequence[str] | None = None,
) -> FxReconciliationCliArguments:
    """Parse raw CLI arguments into FxReconciliationCliArguments."""
    parser = build_fx_reconciliation_cli_parser()
    args = parser.parse_args(argv)
    return extract_fx_reconciliation_arguments(args)
