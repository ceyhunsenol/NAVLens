import math
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    FxRateKind,
    FxReturnPolicy,
    MarketDate,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnPeriod,
)
from navlens.alignment.cli_args import AlignmentCliArguments
from navlens.alignment.fx_return_contribution_tcmb_cli_args import (
    FxReturnContributionTcmbCliArguments,
    InvalidFxReturnContributionTcmbCliArgumentsError,
    build_fx_return_contribution_tcmb_cli_parser,
    extract_fx_return_contribution_tcmb_cli_arguments,
    parse_fx_return_contribution_tcmb_cli_arguments,
)
from navlens.alignment.request import PointInTimeAlignmentRequest
from navlens.sources.tcmb import TcmbCachePolicy
from navlens.sources.tcmb.composition import TcmbSourceSettings


def _valid_cli_argv(tmp_path: Path) -> list[str]:
    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text("fund_id\n", encoding="utf-8")
    prices_file = tmp_path / "prices.csv"
    prices_file.write_text("price\n", encoding="utf-8")
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True, exist_ok=True)

    return [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "TEST_FUND",
        "--holdings-source-id",
        "src_h",
        "--security-price-source-id",
        "src_p",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "unadjusted",
        "--prediction-timestamp",
        "2026-01-02T10:00:00Z",
        "--pricing-as-of-date",
        "2026-01-02",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-01",
        "--return-end-date",
        "2026-01-02",
        "--required-fx-rate-kind",
        "non_cash_buying",
        "--max-fx-staleness-calendar-days",
        "3",
        "--price-history-start-date",
        "2026-01-01",
        "--tcmb-cache-root",
        str(cache_root),
        "--tcmb-cache-policy",
        "cache_only",
    ]


_DEFAULT_PERMIT_FOREIGN = PriceCurrencyPolicy("permit_foreign")
_DEFAULT_PRICING_AS_OF = MarketDate(2026, 1, 2)


def _make_dummy_alignment_args(
    tmp_path: Path,
    price_currency_policy: PriceCurrencyPolicy = _DEFAULT_PERMIT_FOREIGN,
    pricing_as_of: MarketDate = _DEFAULT_PRICING_AS_OF,
) -> AlignmentCliArguments:
    base_policy = AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        pricing_as_of_date=pricing_as_of,
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )
    policy = base_policy.with_price_currency_policy(price_currency_policy)
    request = PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
        policy=policy,
    )
    return AlignmentCliArguments(
        holdings_csv=tmp_path / "holdings.csv",
        security_prices_csv=tmp_path / "prices.csv",
        request=request,
    )


def test_parse_valid_arguments_with_defaults(tmp_path: Path) -> None:
    argv = _valid_cli_argv(tmp_path)
    args = parse_fx_return_contribution_tcmb_cli_arguments(argv)

    assert args.price_history_start_date == date(2026, 1, 1)
    assert args.closed_dates == ()
    assert args.target_period == ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    assert args.fx_policy == FxReturnPolicy(FxRateKind("non_cash_buying"), 3)
    assert args.tcmb_source_settings.cache_policy == TcmbCachePolicy.cache_only
    assert args.tcmb_source_settings.http_timeout_seconds == 30.0
    assert args.alignment_args.request.policy.price_currency_policy == PriceCurrencyPolicy(
        "permit_foreign"
    )


def test_parse_explicit_cache_policies_and_timeout(tmp_path: Path) -> None:
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--tcmb-cache-policy") + 1] = "prefer_cache"
    argv.extend(["--tcmb-http-timeout-seconds", "45.5"])

    args = parse_fx_return_contribution_tcmb_cli_arguments(argv)
    assert args.tcmb_source_settings.cache_policy == TcmbCachePolicy.prefer_cache
    assert args.tcmb_source_settings.http_timeout_seconds == 45.5


def test_parse_repeated_closed_dates(tmp_path: Path) -> None:
    argv = _valid_cli_argv(tmp_path) + [
        "--closed-date",
        "2026-01-15",
        "--closed-date",
        "2026-01-16",
    ]
    args = parse_fx_return_contribution_tcmb_cli_arguments(argv)
    assert args.closed_dates == (date(2026, 1, 15), date(2026, 1, 16))


def test_duplicate_closed_date_raises_typed_error(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path) + [
        "--closed-date",
        "2026-01-15",
        "--closed-date",
        "2026-01-15",
    ]
    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="closed_dates must not contain duplicates",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


def test_invalid_price_history_start_date_raises_typed_error(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--price-history-start-date") + 1] = "invalid-date"

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="invalid price_history_start_date",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


def test_price_history_start_date_after_pricing_as_of_raises_typed_error(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--price-history-start-date") + 1] = "2026-01-05"

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="cannot be after pricing_as_of_date",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


def test_invalid_return_period_dates_raises_typed_error(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--return-start-date") + 1] = "2026-01-05"
    argv[argv.index("--return-end-date") + 1] = "2026-01-02"

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="invalid return period",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


def test_invalid_fx_policy_staleness_raises_typed_error(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--max-fx-staleness-calendar-days") + 1] = "-1"

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="invalid FX return policy",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


@pytest.mark.parametrize("timeout", [0.0, -1.0, -0.01, math.nan, math.inf])
def test_invalid_timeout_raises_typed_error(tmp_path: Path, timeout: float) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path) + ["--tcmb-http-timeout-seconds", str(timeout)]

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="tcmb_http_timeout_seconds must be a finite positive number",
    ):
        extract_fx_return_contribution_tcmb_cli_arguments(parsed_ns)


def test_missing_argument_exits_with_2(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv.remove("--required-fx-rate-kind")
    argv.remove("non_cash_buying")

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2


def test_invalid_cache_policy_choice_exits_with_2(tmp_path: Path) -> None:
    parser = build_fx_return_contribution_tcmb_cli_parser()
    argv = _valid_cli_argv(tmp_path)
    argv[argv.index("--tcmb-cache-policy") + 1] = "invalid_policy"

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2


def test_direct_dataclass_invariant_validation(tmp_path: Path) -> None:
    alignment_args = _make_dummy_alignment_args(tmp_path)
    settings = TcmbSourceSettings(
        cache_root=tmp_path,
        cache_policy=TcmbCachePolicy.cache_only,
    )
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    fx_policy = FxReturnPolicy(FxRateKind("non_cash_buying"), 3)

    # Valid direct construction
    args = FxReturnContributionTcmbCliArguments(
        alignment_args=alignment_args,
        price_history_start_date=date(2026, 1, 1),
        closed_dates=(date(2026, 1, 15),),
        fx_policy=fx_policy,
        target_period=period,
        tcmb_source_settings=settings,
    )
    assert args.price_history_start_date == date(2026, 1, 1)

    # Invariant failure: wrong price currency policy
    strict_alignment_args = _make_dummy_alignment_args(
        tmp_path, price_currency_policy=PriceCurrencyPolicy("fund_base_only")
    )
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="alignment policy must use permit_foreign",
    ):
        FxReturnContributionTcmbCliArguments(
            alignment_args=strict_alignment_args,
            price_history_start_date=date(2026, 1, 1),
            closed_dates=(),
            fx_policy=fx_policy,
            target_period=period,
            tcmb_source_settings=settings,
        )

    # Invariant failure: price_history_start_date after pricing_as_of_date
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="cannot be after pricing_as_of_date",
    ):
        FxReturnContributionTcmbCliArguments(
            alignment_args=alignment_args,
            price_history_start_date=date(2026, 1, 5),
            closed_dates=(),
            fx_policy=fx_policy,
            target_period=period,
            tcmb_source_settings=settings,
        )

    # Invariant failure: duplicate closed dates
    with pytest.raises(
        InvalidFxReturnContributionTcmbCliArgumentsError,
        match="closed_dates must not contain duplicates",
    ):
        FxReturnContributionTcmbCliArguments(
            alignment_args=alignment_args,
            price_history_start_date=date(2026, 1, 1),
            closed_dates=(date(2026, 1, 15), date(2026, 1, 15)),
            fx_policy=fx_policy,
            target_period=period,
            tcmb_source_settings=settings,
        )
