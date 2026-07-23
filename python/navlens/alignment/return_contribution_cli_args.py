"""Command-line argument parsing for point-in-time return contribution."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from navlens import ReturnPeriod

from .cli_args import (
    AlignmentCliArguments,
    build_alignment_cli_parser,
    extract_alignment_arguments,
    parse_market_date,
)


@dataclass(frozen=True, slots=True)
class ReturnContributionCliArguments:
    """Parsed and validated command-line inputs for return contribution CLI."""

    alignment_args: AlignmentCliArguments
    target_period: ReturnPeriod


def build_return_contribution_cli_parser() -> argparse.ArgumentParser:
    """Build parser for navlens-return-contribution-csv."""
    parser = build_alignment_cli_parser(
        prog="navlens-return-contribution-csv",
        description="Calculate return contribution from CSV holdings and security prices.",
    )
    parser.add_argument(
        "--return-start-date",
        required=True,
        type=str,
        help="Return period start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--return-end-date",
        required=True,
        type=str,
        help="Return period end date (YYYY-MM-DD).",
    )
    return parser


def parse_return_contribution_cli_arguments(
    argv: Sequence[str] | None = None,
) -> ReturnContributionCliArguments:
    """Parse raw CLI arguments into ReturnContributionCliArguments."""
    parser = build_return_contribution_cli_parser()
    args = parser.parse_args(argv)

    alignment_args = extract_alignment_arguments(args)
    period = ReturnPeriod(
        parse_market_date(args.return_start_date),
        parse_market_date(args.return_end_date),
    )

    return ReturnContributionCliArguments(
        alignment_args=alignment_args,
        target_period=period,
    )
