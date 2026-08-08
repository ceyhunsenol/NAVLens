from pathlib import Path
from unittest.mock import patch

import pytest
from navlens import calculate_point_in_time_fx_adjusted_return_contribution
from navlens.alignment.fx_return_contribution_cli import main

HOLDINGS_CSV_HEADER = (
    "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
)
PRICES_CSV_HEADER = (
    "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
)
FX_CSV_HEADER = (
    "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at\n"
)


def create_holdings_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(HOLDINGS_CSV_HEADER + "".join(rows), encoding="utf-8")
    return path


def create_prices_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(PRICES_CSV_HEADER + "".join(rows), encoding="utf-8")
    return path


def create_fx_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(FX_CSV_HEADER + "".join(rows), encoding="utf-8")
    return path


def build_argv(
    holdings_csv: Path,
    prices_csv: Path,
    fx_csv: Path,
    return_start: str = "2026-01-01",
    return_end: str = "2026-01-31",
    fx_source_id: str = "tcmb",
    required_fx_rate_kind: str = "non_cash_buying",
    max_fx_staleness: str = "0",
) -> list[str]:
    return [
        "--holdings-csv",
        str(holdings_csv),
        "--security-prices-csv",
        str(prices_csv),
        "--fx-rates-csv",
        str(fx_csv),
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap_src",
        "--security-price-source-id",
        "bloomberg",
        "--fx-source-id",
        fx_source_id,
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "unadjusted",
        "--required-fx-rate-kind",
        required_fx_rate_kind,
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "0",
        "--max-fx-staleness-calendar-days",
        max_fx_staleness,
        "--return-start-date",
        return_start,
        "--return-end-date",
        return_end,
    ]


def test_cli_help_and_missing_arguments() -> None:
    with pytest.raises(SystemExit) as exc_info_help:
        main(["--help"])
    assert exc_info_help.value.code == 0

    with pytest.raises(SystemExit) as exc_info_missing:
        main([])
    assert exc_info_missing.value.code == 2


def test_successful_usd_try_end_to_end_execution(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    out = captured.out
    assert captured.err == ""

    assert "Holdings Source ID: kap_src" in out
    assert "Security Price Source ID: bloomberg" in out
    assert "FX Source ID: tcmb" in out
    assert "Required FX Rate Kind: non_cash_buying" in out
    assert "Target Period: 2026-01-01 to 2026-01-31" in out
    assert "Observed Contribution: 0.210000" in out
    assert "effective return: 0.210000" in out
    assert "weighted contribution: 0.210000" in out
    assert "source_id: tcmb, pair: USD/TRY, kind: non_cash_buying" in out


def test_same_currency_execution_without_required_fx_observations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_TRY,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_TRY,2026-01-01,100.0,TRY,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_TRY,2026-01-31,110.0,TRY,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    # Valid FX CSV with unrelated pair/source/kind
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "other_src,EUR,USD,2026-01-01,1.08,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "other_src,EUR,USD,2026-01-31,1.10,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "fx return: not_required" in out
    assert "effective return: 0.100000" in out

    prov_idx = out.index("Selected FX Snapshots Provenance:")
    assert "(none)" in out[prov_idx:]


def test_mixed_try_usd_partial_coverage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        [
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,0.5\n",
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_EUR,equity,0.5\n",
        ],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_EUR,2026-01-01,100.0,EUR,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_EUR,2026-01-31,110.0,EUR,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    # Provide only USD/TRY
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "reason: missing_direct_fx_candidate" in out
    assert "required pair: EUR/TRY" in out
    assert "required kind: non_cash_buying" in out


def test_provider_and_rate_kind_isolation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "other,USD,TRY,2026-01-01,29.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-01,30.5,cash_selling,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(
        holdings, prices, fx, fx_source_id="tcmb", required_fx_rate_kind="non_cash_buying"
    )

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "source_id: tcmb, pair: USD/TRY, kind: non_cash_buying" in out
    assert "source_id: other" not in out
    assert "kind: cash_selling" not in out


def test_future_fx_correction_exclusion(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            # Published after prediction timestamp 2026-02-01T12:00:00Z
            "tcmb,USD,TRY,2026-01-31,35.0,non_cash_buying,2026-02-02T12:00:00Z,2026-02-02T12:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "rate: 33.000000" in out
    assert "rate: 35.000000" not in out


def test_missing_direct_pair_formatting(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    # Only EUR/TRY in FX CSV
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,EUR,TRY,2026-01-01,32.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,EUR,TRY,2026-01-31,35.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "reason: missing_direct_fx_candidate" in out
    assert "required pair: USD/TRY" in out
    assert "required kind: non_cash_buying" in out


def test_stale_start_and_end_fx_evidence_formatting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-05,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    # Start FX observation is on Jan 1 (staleness 4d relative to requested Jan 5)
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    # Allowed staleness 5d -> applied evidence formatted with staleness
    argv = build_argv(
        holdings,
        prices,
        fx,
        return_start="2026-01-05",
        return_end="2026-01-31",
        max_fx_staleness="5",
    )

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "start: 2026-01-01 [stale: 4d]" in out
    assert "end: 2026-01-31 [stale: 0d]" in out

    # Test when staleness exceeds max allowed -> stale_fx_start_observation gap
    argv_stale = build_argv(
        holdings,
        prices,
        fx,
        return_start="2026-01-05",
        return_end="2026-01-31",
        max_fx_staleness="1",
    )
    exit_code_stale = main(argv_stale)
    assert exit_code_stale == 0

    out_stale = capsys.readouterr().out
    assert "reason: stale_fx_start_observation" in out_stale
    assert "requested date: 2026-01-05" in out_stale
    assert "actual date: 2026-01-01" in out_stale
    assert "staleness: 4d" in out_stale
    assert "max allowed: 1d" in out_stale

    end_stale_prices = create_prices_csv(
        tmp_path / "end_stale_prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    end_stale_fx = create_fx_csv(
        tmp_path / "end_stale_fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n"
        ],
    )
    end_stale_argv = build_argv(
        holdings,
        end_stale_prices,
        end_stale_fx,
        max_fx_staleness="1",
    )

    assert main(end_stale_argv) == 0
    end_stale_output = capsys.readouterr().out
    assert "reason: stale_fx_end_observation" in end_stale_output
    assert "requested date: 2026-01-31" in end_stale_output
    assert "actual date: 2026-01-01" in end_stale_output
    assert "staleness: 30d" in end_stale_output
    assert "max allowed: 1d" in end_stale_output


def test_deterministic_component_gap_and_provenance_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        [
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_EUR,equity,0.5\n",
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,0.5\n",
        ],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_EUR,2026-01-01,100.0,EUR,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_EUR,2026-01-31,110.0,EUR,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,EUR,TRY,2026-01-01,32.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,EUR,TRY,2026-01-31,35.2,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    exit_code = main(argv)
    assert exit_code == 0

    out = capsys.readouterr().out
    # Components follow canonical Rust result order.
    components_idx = out.index("Component Contributions:")
    eur_idx = out.index("INST_EUR", components_idx)
    usd_idx = out.index("INST_USD", components_idx)
    assert eur_idx < usd_idx

    # Selected FX provenance follows canonical pair order EUR/TRY then USD/TRY
    prov_idx = out.index("Selected FX Snapshots Provenance:")
    eur_prov_idx = out.index("pair: EUR/TRY", prov_idx)
    usd_prov_idx = out.index("pair: USD/TRY", prov_idx)
    assert eur_prov_idx < usd_prov_idx

    unrelated_fx = create_fx_csv(
        tmp_path / "unrelated_fx.csv",
        [
            "tcmb,GBP,TRY,2026-01-01,40.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n"
        ],
    )
    assert main(build_argv(holdings, prices, unrelated_fx)) == 0
    gap_output = capsys.readouterr().out
    gaps_idx = gap_output.index("Return Gaps:")
    eur_gap_idx = gap_output.index("INST_EUR", gaps_idx)
    usd_gap_idx = gap_output.index("INST_USD", gaps_idx)
    assert eur_gap_idx < usd_gap_idx


def test_invalid_timestamps_dates_and_identifiers_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )

    # Invalid prediction timestamp
    argv = build_argv(holdings, prices, fx)
    argv[argv.index("--prediction-timestamp") + 1] = "not-a-timestamp"
    assert main(argv) == 1
    assert "error: " in capsys.readouterr().err

    # Invalid return start date
    argv_date = build_argv(holdings, prices, fx, return_start="invalid-date")
    assert main(argv_date) == 1
    assert "error: " in capsys.readouterr().err

    argv_identifier = build_argv(holdings, prices, fx, fx_source_id="   ")
    assert main(argv_identifier) == 1
    assert "fx_source_id must be a non-empty" in capsys.readouterr().err


def test_missing_and_malformed_csv_files_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = tmp_path / "non_existent_holdings.csv"
    prices = tmp_path / "non_existent_prices.csv"
    fx = tmp_path / "non_existent_fx.csv"

    argv = build_argv(holdings, prices, fx)
    assert main(argv) == 1

    err = capsys.readouterr().err
    assert "error: " in err

    # Malformed FX CSV
    malformed_fx = tmp_path / "malformed_fx.csv"
    malformed_fx.write_text("invalid,header\n", encoding="utf-8")
    valid_holdings = create_holdings_csv(
        tmp_path / "h.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,1.0\n"],
    )
    valid_prices = create_prices_csv(
        tmp_path / "p.csv",
        [
            "bloomberg,INST1,2026-01-01,100.0,TRY,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST1,2026-01-31,110.0,TRY,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv_malformed = build_argv(valid_holdings, valid_prices, malformed_fx)
    assert main(argv_malformed) == 1
    assert "error: CSV is missing required columns in" in capsys.readouterr().err


def test_proof_of_delegation_to_existing_orchestration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST_USD,equity,1.0\n"],
    )
    prices = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST_USD,2026-01-01,100.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST_USD,2026-01-31,110.0,USD,unadjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    fx = create_fx_csv(
        tmp_path / "fx.csv",
        [
            "tcmb,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "tcmb,USD,TRY,2026-01-31,33.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings, prices, fx)

    with patch(
        "navlens.alignment.fx_return_contribution_csv.calculate_point_in_time_fx_adjusted_return_contribution",
        wraps=calculate_point_in_time_fx_adjusted_return_contribution,
    ) as mock_orchestration:
        exit_code = main(argv)
        assert exit_code == 0
        assert mock_orchestration.call_count == 1
