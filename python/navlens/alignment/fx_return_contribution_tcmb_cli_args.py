"""Command-line argument parsing for TCMB-backed FX-adjusted return contribution."""

import argparse
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from navlens import (
    FxRateKind,
    FxReturnPolicy,
    NavlensValidationError,
    PriceCurrencyPolicy,
    ReturnPeriod,
)
from navlens.sources.tcmb import TcmbAcquisitionError, TcmbCachePolicy
from navlens.sources.tcmb.composition import TcmbSourceSettings

from .cli_args import (
    AlignmentCliArguments,
    build_alignment_cli_parser,
    extract_alignment_arguments,
    parse_market_date,
)


class InvalidFxReturnContributionTcmbCliArgumentsError(ValueError):
    """Raised when FX return contribution TCMB CLI arguments fail validation."""


@dataclass(frozen=True, slots=True)
class FxReturnContributionTcmbCliArguments:
    """Parsed and validated command-line inputs for TCMB FX return contribution CLI."""

    alignment_args: AlignmentCliArguments
    price_history_start_date: date
    closed_dates: tuple[date, ...]
    fx_policy: FxReturnPolicy
    target_period: ReturnPeriod
    tcmb_source_settings: TcmbSourceSettings

    def __post_init__(self) -> None:
        _validate_argument_contract(self)


def build_fx_return_contribution_tcmb_cli_parser(
    prog: str = "navlens-fx-return-contribution-tcmb",
    description: str = (
        "Calculate FX-adjusted return contribution using CSV holdings, "
        "security prices, and TCMB exchange rates."
    ),
) -> argparse.ArgumentParser:
    """Build parser for navlens-fx-return-contribution-tcmb CLI."""
    parser = build_alignment_cli_parser(
        prog=prog,
        description=description,
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


def extract_fx_return_contribution_tcmb_cli_arguments(
    args: argparse.Namespace,
) -> FxReturnContributionTcmbCliArguments:
    """Extract and validate FxReturnContributionTcmbCliArguments from a parsed namespace."""
    base_alignment_args = extract_alignment_arguments(args)

    permit_foreign_policy = base_alignment_args.request.policy.with_price_currency_policy(
        PriceCurrencyPolicy("permit_foreign")
    )
    updated_request = replace(base_alignment_args.request, policy=permit_foreign_policy)
    updated_alignment_args = replace(base_alignment_args, request=updated_request)

    price_history_start_date = _parse_price_history_start_date(args.price_history_start_date)
    closed_dates = _parse_closed_dates(args.closed_date)
    target_period = _build_return_period(args.return_start_date, args.return_end_date)
    fx_policy = _build_fx_return_policy(
        args.required_fx_rate_kind, args.max_fx_staleness_calendar_days
    )
    cache_policy = _parse_cache_policy(args.tcmb_cache_policy)
    timeout_seconds = _validate_timeout_seconds(args.tcmb_http_timeout_seconds)

    try:
        settings = TcmbSourceSettings(
            cache_root=Path(args.tcmb_cache_root),
            cache_policy=cache_policy,
            http_timeout_seconds=timeout_seconds,
        )
    except TcmbAcquisitionError as error:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(str(error)) from error

    return FxReturnContributionTcmbCliArguments(
        alignment_args=updated_alignment_args,
        price_history_start_date=price_history_start_date,
        closed_dates=closed_dates,
        fx_policy=fx_policy,
        target_period=target_period,
        tcmb_source_settings=settings,
    )


def parse_fx_return_contribution_tcmb_cli_arguments(
    argv: Sequence[str] | None = None,
) -> FxReturnContributionTcmbCliArguments:
    """Parse raw CLI arguments into FxReturnContributionTcmbCliArguments."""
    parser = build_fx_return_contribution_tcmb_cli_parser()
    parsed_args = parser.parse_args(argv)
    return extract_fx_return_contribution_tcmb_cli_arguments(parsed_args)


def _parse_price_history_start_date(raw_value: object) -> date:
    if isinstance(raw_value, date):
        return raw_value
    if not isinstance(raw_value, str):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"price_history_start_date must be a string or date, got {type(raw_value).__name__}"
        )
    try:
        return date.fromisoformat(raw_value)
    except ValueError as error:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"invalid price_history_start_date {raw_value!r}: {error}"
        ) from error


def _parse_closed_dates(raw_values: object) -> tuple[date, ...]:
    if not isinstance(raw_values, (list, tuple)):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "closed_date values must be a sequence"
        )
    parsed: list[date] = []
    for raw in raw_values:
        if isinstance(raw, date):
            parsed.append(raw)
        elif isinstance(raw, str):
            try:
                parsed.append(date.fromisoformat(raw))
            except ValueError as error:
                raise InvalidFxReturnContributionTcmbCliArgumentsError(
                    f"invalid closed_date {raw!r}: {error}"
                ) from error
        else:
            raise InvalidFxReturnContributionTcmbCliArgumentsError(
                f"closed_date must be a string or date, got {type(raw).__name__}"
            )
    return tuple(parsed)


def _build_return_period(start_str: object, end_str: object) -> ReturnPeriod:
    try:
        start_date = parse_market_date(start_str)
        end_date = parse_market_date(end_str)
        return ReturnPeriod(start_date, end_date)
    except (NavlensValidationError, ValueError) as error:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"invalid return period ({start_str!r}, {end_str!r}): {error}"
        ) from error


def _build_fx_return_policy(kind_str: object, staleness_days: object) -> FxReturnPolicy:
    if not isinstance(kind_str, str):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"required_fx_rate_kind must be a string, got {type(kind_str).__name__}"
        )
    if isinstance(staleness_days, bool) or not isinstance(staleness_days, int):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"max_fx_staleness_calendar_days must be an int, got {type(staleness_days).__name__}"
        )
    try:
        kind = FxRateKind(kind_str)
        return FxReturnPolicy(kind, staleness_days)
    except (NavlensValidationError, OverflowError, ValueError) as error:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"invalid FX return policy ({kind_str!r}, {staleness_days!r}): {error}"
        ) from error


def _parse_cache_policy(raw_policy: object) -> TcmbCachePolicy:
    if isinstance(raw_policy, TcmbCachePolicy):
        return raw_policy
    if not isinstance(raw_policy, str):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"tcmb_cache_policy must be a string, got {type(raw_policy).__name__}"
        )
    try:
        return TcmbCachePolicy(raw_policy)
    except ValueError as error:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"invalid tcmb_cache_policy {raw_policy!r}: {error}"
        ) from error


def _validate_timeout_seconds(raw_timeout: object) -> float:
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"tcmb_http_timeout_seconds must be a float, got {type(raw_timeout).__name__}"
        )
    timeout = float(raw_timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"tcmb_http_timeout_seconds must be a finite positive number, got {raw_timeout}"
        )
    return timeout


def _validate_argument_contract(arguments: FxReturnContributionTcmbCliArguments) -> None:
    if not isinstance(arguments.alignment_args, AlignmentCliArguments):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "alignment_args must be an AlignmentCliArguments instance"
        )
    expected_curr_policy = PriceCurrencyPolicy("permit_foreign")
    actual_curr_policy = arguments.alignment_args.request.policy.price_currency_policy
    if actual_curr_policy != expected_curr_policy:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"alignment policy must use permit_foreign, got {actual_curr_policy}"
        )
    if type(arguments.price_history_start_date) is not date:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "price_history_start_date must be an exact date instance"
        )
    pricing_as_of = date.fromisoformat(
        str(arguments.alignment_args.request.policy.pricing_as_of_date)
    )
    if arguments.price_history_start_date > pricing_as_of:
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            f"price_history_start_date ({arguments.price_history_start_date}) "
            f"cannot be after pricing_as_of_date ({pricing_as_of})"
        )
    _validate_closed_date_contract(arguments.closed_dates)
    if not isinstance(arguments.fx_policy, FxReturnPolicy):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "fx_policy must be an FxReturnPolicy instance"
        )
    if not isinstance(arguments.target_period, ReturnPeriod):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "target_period must be a ReturnPeriod instance"
        )
    if not isinstance(arguments.tcmb_source_settings, TcmbSourceSettings):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "tcmb_source_settings must be a TcmbSourceSettings instance"
        )


def _validate_closed_date_contract(closed_dates: object) -> None:
    if not isinstance(closed_dates, tuple) or not all(
        type(value) is date for value in closed_dates
    ):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "closed_dates must be a tuple of exact date instances"
        )
    if len(set(closed_dates)) != len(closed_dates):
        raise InvalidFxReturnContributionTcmbCliArgumentsError(
            "closed_dates must not contain duplicates"
        )
