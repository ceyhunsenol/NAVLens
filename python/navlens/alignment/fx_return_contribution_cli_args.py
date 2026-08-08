"""Command-line argument parsing for FX-adjusted point-in-time return contribution."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from navlens import FxRateKind, FxReturnPolicy, PriceCurrencyPolicy, ReturnPeriod

from .cli_args import (
    AlignmentCliArguments,
    build_alignment_cli_parser,
    extract_alignment_arguments,
    parse_market_date,
)


@dataclass(frozen=True, slots=True)
class FxReturnContributionCliArguments:
    """Parsed and validated command-line inputs for FX return contribution CLI."""

    alignment_args: AlignmentCliArguments
    fx_rates_csv: Path
    fx_source_id: str
    fx_policy: FxReturnPolicy
    target_period: ReturnPeriod


def build_fx_return_contribution_cli_parser(
    prog: str = "navlens-fx-return-contribution-csv",
    description: str = (
        "Calculate FX-adjusted return contribution from CSV holdings, "
        "security prices, and FX rates."
    ),
) -> argparse.ArgumentParser:
    """Build parser for navlens-fx-return-contribution-csv CLI."""
    parser = build_alignment_cli_parser(
        prog=prog,
        description=description,
    )
    parser.add_argument(
        "--fx-rates-csv",
        required=True,
        type=Path,
        help="Path to FX rates CSV.",
    )
    parser.add_argument(
        "--fx-source-id",
        required=True,
        type=str,
        help="FX rate source identifier.",
    )
    parser.add_argument(
        "--required-fx-rate-kind",
        required=True,
        type=str,
        help="Required FX rate kind (e.g. non_cash_buying).",
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
    parser.add_argument(
        "--max-fx-staleness-calendar-days",
        required=True,
        type=int,
        help="Maximum allowed FX staleness in calendar days.",
    )
    return parser


def extract_fx_return_contribution_arguments(
    args: argparse.Namespace,
) -> FxReturnContributionCliArguments:
    """Extract FxReturnContributionCliArguments from a parsed namespace."""
    base_alignment_args = extract_alignment_arguments(args)

    permit_foreign_policy = base_alignment_args.request.policy.with_price_currency_policy(
        PriceCurrencyPolicy("permit_foreign")
    )
    updated_request = replace(base_alignment_args.request, policy=permit_foreign_policy)
    updated_alignment_args = replace(base_alignment_args, request=updated_request)

    period = ReturnPeriod(
        parse_market_date(args.return_start_date),
        parse_market_date(args.return_end_date),
    )
    fx_policy = FxReturnPolicy(
        FxRateKind(args.required_fx_rate_kind),
        args.max_fx_staleness_calendar_days,
    )

    return FxReturnContributionCliArguments(
        alignment_args=updated_alignment_args,
        fx_rates_csv=args.fx_rates_csv,
        fx_source_id=args.fx_source_id,
        fx_policy=fx_policy,
        target_period=period,
    )


def parse_fx_return_contribution_cli_arguments(
    argv: Sequence[str] | None = None,
) -> FxReturnContributionCliArguments:
    """Parse raw CLI arguments into FxReturnContributionCliArguments."""
    parser = build_fx_return_contribution_cli_parser()
    parsed_args = parser.parse_args(argv)
    return extract_fx_return_contribution_arguments(parsed_args)
