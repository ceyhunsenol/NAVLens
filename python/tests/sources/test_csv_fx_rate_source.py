"""Tests for CsvFxRateSource adapter."""

from datetime import date
from pathlib import Path

import pytest
from navlens import CurrencyCode, CurrencyPair, FxRate, FxRateKind
from navlens.datasets import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateSourceUnavailableError,
)
from navlens.sources import (
    CsvFxRateSource,
    CsvFxRateSourceError,
    CsvFxRateUnavailableError,
)

SAMPLE_CSV = "\n".join(
    [
        "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at",
        "manual,USD,TRY,2026-07-20,34.0,non_cash_buying,2026-07-20T15:30:00Z,2026-07-20T15:35:00Z",
        "manual,USD,TRY,2026-07-20,34.2,non_cash_buying,2026-07-20T16:00:00Z,2026-07-20T16:05:00Z",
        "manual,USD,TRY,2026-07-21,34.5,non_cash_buying,2026-07-21T15:30:00Z,2026-07-21T15:35:00Z",
        "manual,USD,TRY,2026-07-22,34.8,non_cash_buying,2026-07-22T15:30:00Z,2026-07-22T15:35:00Z",
        "manual,USD,TRY,2026-07-20,34.1,non_cash_selling,2026-07-20T15:30:00Z,2026-07-20T15:35:00Z",
        "manual,EUR,TRY,2026-07-20,37.0,non_cash_buying,2026-07-20T15:30:00Z,2026-07-20T15:35:00Z",
        "other_src,USD,TRY,2026-07-20,99.0,non_cash_buying,2026-07-20T15:30:00Z,2026-07-20T15:35:00Z",
        "",
    ]
)


def test_csv_source_rejects_invalid_source_id(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        CsvFxRateSource(csv_file, "")
    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        CsvFxRateSource(csv_file, "   ")
    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        CsvFxRateSource(csv_file, 123)  # type: ignore[arg-type]


def test_csv_source_binds_to_single_source_id(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    source = CsvFxRateSource(csv_file, "  manual  ")
    assert source.source_id == "manual"
    assert source.path == csv_file

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    snapshots = source.fetch_fx_rates(query)

    # 2 revisions on 07-20 + 1 on 07-21 + 1 on 07-22 = 4
    assert len(snapshots) == 4
    # Ensure rows from 'other_src' are excluded
    assert all(s.source_id == "manual" for s in snapshots)
    assert [s.observation.rate for s in snapshots] == [
        FxRate(34.0),
        FxRate(34.2),
        FxRate(34.5),
        FxRate(34.8),
    ]


def test_csv_source_filters_by_date_range(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 21),
        end_date=date(2026, 7, 21),
    )
    snapshots = source.fetch_fx_rates(query)

    assert len(snapshots) == 1
    assert snapshots[0].observation.rate == FxRate(34.5)


def test_csv_source_preserves_source_file_order_and_duplicate_date_revisions(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 20),
    )
    snapshots = source.fetch_fx_rates(query)

    # Both same-date revisions are returned uncollapsed in exact file order
    assert len(snapshots) == 2
    assert snapshots[0].observation.rate == FxRate(34.0)
    assert snapshots[1].observation.rate == FxRate(34.2)


def test_csv_source_preserves_original_snapshot_identity(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    fetch1 = source.fetch_fx_rates(query)
    fetch2 = source.fetch_fx_rates(query)

    assert len(fetch1) == 4
    assert len(fetch2) == 4
    for snap1, snap2 in zip(fetch1, fetch2, strict=True):
        assert snap1 is snap2


def test_csv_source_reverse_pair_does_not_match(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    # Reversed pair: TRY/USD instead of USD/TRY
    try_usd = CurrencyPair(CurrencyCode("TRY"), CurrencyCode("USD"))
    query = FxRateQuery(
        pair=try_usd,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    snapshots = source.fetch_fx_rates(query)

    assert snapshots == ()


def test_csv_source_different_kind_does_not_match(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    # Query CashBuying (only non_cash_buying and non_cash_selling exist in CSV)
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    snapshots = source.fetch_fx_rates(query)

    assert snapshots == ()


def test_csv_source_valid_interval_with_zero_observations_returns_empty_tuple(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 10),
    )
    snapshots = source.fetch_fx_rates(query)

    assert snapshots == ()


def test_csv_source_absent_pair_returns_empty_tuple(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    gbp_try = CurrencyPair(CurrencyCode("GBP"), CurrencyCode("TRY"))
    query = FxRateQuery(
        pair=gbp_try,
        kind=FxRateKind("non_cash_buying"),
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    snapshots = source.fetch_fx_rates(query)

    assert snapshots == ()


def test_csv_source_rejects_non_query_type(tmp_path: Path) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvFxRateSource(csv_file, "manual")

    with pytest.raises(TypeError, match="FxRateQuery"):
        source.fetch_fx_rates("USDTRY")  # type: ignore[arg-type]


def test_csv_source_missing_file_raises_unavailable(tmp_path: Path) -> None:
    missing_file = tmp_path / "nonexistent.csv"

    with pytest.raises(FxRateSourceUnavailableError) as exc_info:
        CsvFxRateSource(missing_file, "manual")

    assert isinstance(exc_info.value.__cause__, CsvFxRateUnavailableError)


def test_csv_source_corrupted_data_raises_corrupted_error(tmp_path: Path) -> None:
    corrupted_file = tmp_path / "corrupted.csv"
    corrupted_file.write_text("invalid,header,only\n1,2,3", encoding="utf-8")

    with pytest.raises(FxRateCorruptedSourceDataError) as exc_info:
        CsvFxRateSource(corrupted_file, "manual")

    assert isinstance(exc_info.value.__cause__, CsvFxRateSourceError)
