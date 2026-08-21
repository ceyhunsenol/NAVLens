"""Command-line argument parsing for TCMB-backed historical FX reconciliation."""

import argparse
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens import (
    FxRateKind,
)
from navlens.sources.tcmb import TCMB_SOURCE_ID, TcmbCachePolicy

from .historical.fx_schedule_csv import HistoricalFxReconciliationRunConfiguration
from .historical_cli_args import (
    HistoricalReconciliationCliArguments,
    add_historical_reconciliation_cli_arguments,
    extract_historical_reconciliation_cli_arguments,
)


class InvalidHistoricalFxTcmbCliArgumentsError(ValueError):
    """Raised when historical FX TCMB CLI arguments fail validation."""


@dataclass(frozen=True, slots=True)
class HistoricalFxTcmbCliArguments:
    """Parsed and validated CLI inputs for TCMB historical FX reconciliation."""

    base_arguments: HistoricalReconciliationCliArguments
    price_history_start_date: date
    closed_dates: tuple[date, ...]
    tcmb_cache_root: Path
    tcmb_cache_policy: TcmbCachePolicy
    tcmb_http_timeout_seconds: float
    config: HistoricalFxReconciliationRunConfiguration

    def __post_init__(self) -> None:
        _validate_argument_contract(self)


def build_historical_fx_tcmb_cli_parser(
    prog: str = "navlens-evaluate-historical-fx-reconciliation-tcmb",
    description: str = (
        "Evaluate historical FX-adjusted fund return reconciliation using TCMB rates."
    ),
) -> argparse.ArgumentParser:
    """Build argument parser for TCMB historical FX reconciliation CLI command."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    add_historical_reconciliation_cli_arguments(parser)
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
    parser.add_argument(
        "--price-history-start-date",
        required=True,
        type=str,
        help="Start date for security price history (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--closed-date",
        action="append",
        default=[],
        type=str,
        help="Market closure date (YYYY-MM-DD) to override as closed. May be repeated.",
    )
    parser.add_argument(
        "--tcmb-cache-root",
        required=True,
        type=Path,
        help="Path to TCMB raw artifact cache directory.",
    )
    parser.add_argument(
        "--tcmb-cache-policy",
        required=True,
        choices=["cache_only", "prefer_cache", "refresh"],
        help="TCMB cache policy (cache_only, prefer_cache, refresh).",
    )
    parser.add_argument(
        "--tcmb-http-timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for TCMB requests (default: 30.0).",
    )
    return parser


def extract_historical_fx_tcmb_cli_arguments(
    args: argparse.Namespace,
) -> HistoricalFxTcmbCliArguments:
    """Extract and validate HistoricalFxTcmbCliArguments from a parsed namespace."""
    base_args = extract_historical_reconciliation_cli_arguments(args)
    price_history_start_date = _parse_price_history_start_date(args.price_history_start_date)
    closed_dates = _parse_closed_dates(args.closed_date)
    cache_policy = _parse_cache_policy(args.tcmb_cache_policy)
    timeout_seconds = _validate_timeout_seconds(args.tcmb_http_timeout_seconds)

    fx_config = HistoricalFxReconciliationRunConfiguration(
        base=base_args.config,
        fx_source_id=TCMB_SOURCE_ID,
        required_fx_rate_kind=FxRateKind(args.required_fx_rate_kind),
        max_fx_staleness_calendar_days=args.max_fx_staleness_calendar_days,
    )

    return HistoricalFxTcmbCliArguments(
        base_arguments=base_args,
        price_history_start_date=price_history_start_date,
        closed_dates=closed_dates,
        tcmb_cache_root=Path(args.tcmb_cache_root),
        tcmb_cache_policy=cache_policy,
        tcmb_http_timeout_seconds=timeout_seconds,
        config=fx_config,
    )


def parse_historical_fx_tcmb_cli_arguments(
    argv: Sequence[str] | None = None,
) -> HistoricalFxTcmbCliArguments:
    """Parse raw CLI arguments into HistoricalFxTcmbCliArguments."""
    parser = build_historical_fx_tcmb_cli_parser()
    args = parser.parse_args(argv)
    return extract_historical_fx_tcmb_cli_arguments(args)


def _parse_price_history_start_date(raw_value: object) -> date:
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"price_history_start_date must be a string or date, got {type(raw_value).__name__}"
        )
    try:
        return date.fromisoformat(raw_value)
    except ValueError as error:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"invalid price_history_start_date {raw_value!r}: {error}"
        ) from error


def _parse_closed_dates(raw_values: object) -> tuple[date, ...]:
    if not isinstance(raw_values, (list, tuple)):
        raise InvalidHistoricalFxTcmbCliArgumentsError("closed_date values must be a sequence")
    parsed: list[date] = []
    for raw in raw_values:
        if isinstance(raw, date):
            parsed.append(raw)
        elif isinstance(raw, str):
            try:
                parsed.append(date.fromisoformat(raw))
            except ValueError as error:
                raise InvalidHistoricalFxTcmbCliArgumentsError(
                    f"invalid closed_date {raw!r}: {error}"
                ) from error
        else:
            raise InvalidHistoricalFxTcmbCliArgumentsError(
                f"closed_date must be a string or date, got {type(raw).__name__}"
            )
    return tuple(parsed)


def _parse_cache_policy(raw_policy: object) -> TcmbCachePolicy:
    if isinstance(raw_policy, TcmbCachePolicy):
        return raw_policy
    if not isinstance(raw_policy, str):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"tcmb_cache_policy must be a string, got {type(raw_policy).__name__}"
        )
    try:
        return TcmbCachePolicy(raw_policy)
    except ValueError as error:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"invalid tcmb_cache_policy {raw_policy!r}: {error}"
        ) from error


def _validate_timeout_seconds(raw_timeout: object) -> float:
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"tcmb_http_timeout_seconds must be a float, got {type(raw_timeout).__name__}"
        )
    timeout = float(raw_timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"tcmb_http_timeout_seconds must be a finite positive number, got {raw_timeout}"
        )
    return timeout


def _validate_argument_contract(arguments: HistoricalFxTcmbCliArguments) -> None:
    if not isinstance(arguments.base_arguments, HistoricalReconciliationCliArguments):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "base_arguments must be a HistoricalReconciliationCliArguments instance"
        )
    if type(arguments.price_history_start_date) is not date:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "price_history_start_date must be an exact date instance"
        )
    _validate_closed_date_contract(arguments.closed_dates)
    if not isinstance(arguments.tcmb_cache_root, Path):
        raise InvalidHistoricalFxTcmbCliArgumentsError("tcmb_cache_root must be a Path")
    if not isinstance(arguments.tcmb_cache_policy, TcmbCachePolicy):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "tcmb_cache_policy must be a TcmbCachePolicy"
        )
    _validate_timeout_seconds(arguments.tcmb_http_timeout_seconds)
    _validate_configuration_contract(arguments)


def _validate_closed_date_contract(closed_dates: object) -> None:
    if not isinstance(closed_dates, tuple) or not all(
        type(value) is date for value in closed_dates
    ):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "closed_dates must be a tuple of exact date instances"
        )
    if len(set(closed_dates)) != len(closed_dates):
        raise InvalidHistoricalFxTcmbCliArgumentsError("closed_dates must not contain duplicates")


def _validate_configuration_contract(arguments: HistoricalFxTcmbCliArguments) -> None:
    if not isinstance(arguments.config, HistoricalFxReconciliationRunConfiguration):
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "config must be a HistoricalFxReconciliationRunConfiguration instance"
        )
    if arguments.config.base is not arguments.base_arguments.config:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            "config.base must be the exact base_arguments.config instance"
        )
    if arguments.config.fx_source_id != TCMB_SOURCE_ID:
        raise InvalidHistoricalFxTcmbCliArgumentsError(
            f"config.fx_source_id must be the canonical TCMB source ID {TCMB_SOURCE_ID!r}"
        )
