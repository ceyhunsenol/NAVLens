"""Command-line argument parsing for historical FX-aware reconciliation evaluation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from navlens import FxRateKind

from .historical.fx_schedule_csv import HistoricalFxReconciliationRunConfiguration
from .historical_cli_args import (
    HistoricalReconciliationCliArguments,
    add_historical_reconciliation_cli_arguments,
    extract_historical_reconciliation_cli_arguments,
)


@dataclass(frozen=True, slots=True)
class HistoricalFxReconciliationCliArguments:
    """Parsed and validated CLI inputs for historical FX reconciliation evaluation."""

    base_arguments: HistoricalReconciliationCliArguments
    fx_rates_csv: Path
    config: HistoricalFxReconciliationRunConfiguration


def build_historical_fx_reconciliation_cli_parser(
    prog: str = "navlens-evaluate-historical-fx-reconciliation-csv",
    description: str = (
        "Evaluate historical FX-adjusted fund return reconciliation over multiple periods."
    ),
) -> argparse.ArgumentParser:
    """Build argument parser for historical FX reconciliation CLI command."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    add_historical_reconciliation_cli_arguments(parser)
    parser.add_argument(
        "--fx-rates-csv",
        required=True,
        type=Path,
        help="Path to CSV containing FX rates.",
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
        "--max-fx-staleness-calendar-days",
        required=True,
        type=int,
        help="Maximum allowed FX rate staleness in calendar days.",
    )
    return parser


def extract_historical_fx_reconciliation_cli_arguments(
    args: argparse.Namespace,
) -> HistoricalFxReconciliationCliArguments:
    """Extract HistoricalFxReconciliationCliArguments from a parsed namespace."""
    base_args = extract_historical_reconciliation_cli_arguments(args)
    fx_config = HistoricalFxReconciliationRunConfiguration(
        base=base_args.config,
        fx_source_id=args.fx_source_id,
        required_fx_rate_kind=FxRateKind(args.required_fx_rate_kind),
        max_fx_staleness_calendar_days=args.max_fx_staleness_calendar_days,
    )
    return HistoricalFxReconciliationCliArguments(
        base_arguments=base_args,
        fx_rates_csv=args.fx_rates_csv,
        config=fx_config,
    )


def parse_historical_fx_reconciliation_cli_arguments(
    argv: Sequence[str] | None = None,
) -> HistoricalFxReconciliationCliArguments:
    """Parse raw CLI arguments into HistoricalFxReconciliationCliArguments."""
    parser = build_historical_fx_reconciliation_cli_parser()
    args = parser.parse_args(argv)
    return extract_historical_fx_reconciliation_cli_arguments(args)
