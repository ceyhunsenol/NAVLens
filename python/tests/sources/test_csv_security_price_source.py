"""Tests for CsvSecurityPriceSource adapter."""

from datetime import date
from pathlib import Path

import pytest
from navlens.datasets import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceSourceUnavailableError,
)
from navlens.sources import (
    CsvSecurityPriceSource,
    CsvSecurityPriceSourceError,
    CsvSecurityPriceUnavailableError,
)

SAMPLE_CSV = "\n".join(
    [
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at",
        "manual,TRY_GARAN,2026-07-20,10.0,TRY,unadjusted,2026-07-20T18:00:00Z,2026-07-20T18:05:00Z",
        "manual,TRY_GARAN,2026-07-21,10.5,TRY,unadjusted,2026-07-21T18:00:00Z,2026-07-21T18:05:00Z",
        "manual,TRY_GARAN,2026-07-22,11.0,TRY,unadjusted,2026-07-22T18:00:00Z,2026-07-22T18:05:00Z",
        "manual,TRY_AKBNK,2026-07-20,15.0,TRY,unadjusted,2026-07-20T18:00:00Z,2026-07-20T18:05:00Z",
        "other_src,TRY_GARAN,2026-07-20,99.0,TRY,unadjusted,2026-07-20T18:00:00Z,2026-07-20T18:05:00Z",
        "",
    ]
)


def test_csv_source_rejects_invalid_source_id(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    with pytest.raises(ValueError, match="source_id"):
        CsvSecurityPriceSource(csv_file, "")
    with pytest.raises(ValueError, match="source_id"):
        CsvSecurityPriceSource(csv_file, "   ")
    with pytest.raises(ValueError, match="source_id"):
        CsvSecurityPriceSource(csv_file, 123)  # type: ignore[arg-type]


def test_csv_source_binds_to_single_source_id(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    source = CsvSecurityPriceSource(csv_file, "  manual  ")
    assert source.source_id == "manual"
    assert source.path == csv_file

    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 20), date(2026, 7, 22))
    snapshots = source.fetch_security_prices(query)

    assert len(snapshots) == 3
    # Ensure rows from 'other_src' are excluded
    assert all(s.source_id == "manual" for s in snapshots)
    assert [s.observation.price.value for s in snapshots] == [10.0, 10.5, 11.0]


def test_csv_source_filters_by_date_range(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvSecurityPriceSource(csv_file, "manual")

    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 21), date(2026, 7, 21))
    snapshots = source.fetch_security_prices(query)

    assert len(snapshots) == 1
    assert snapshots[0].observation.price.value == 10.5


def test_csv_source_valid_interval_with_zero_observations(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvSecurityPriceSource(csv_file, "manual")

    # Dates before any observations
    query = SecurityPriceQuery("TRY_GARAN", date(2026, 7, 1), date(2026, 7, 10))
    snapshots = source.fetch_security_prices(query)

    assert snapshots == ()


def test_csv_source_absent_instrument_returns_empty_tuple(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvSecurityPriceSource(csv_file, "manual")

    query = SecurityPriceQuery("TRY_UNSEEN", date(2026, 7, 20), date(2026, 7, 22))
    snapshots = source.fetch_security_prices(query)

    assert snapshots == ()


def test_csv_source_rejects_non_query_type(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    source = CsvSecurityPriceSource(csv_file, "manual")

    with pytest.raises(TypeError, match="SecurityPriceQuery"):
        source.fetch_security_prices("TRY_GARAN")  # type: ignore[arg-type]


def test_csv_source_missing_file_raises_unavailable(tmp_path: Path) -> None:
    missing_file = tmp_path / "nonexistent.csv"

    with pytest.raises(SecurityPriceSourceUnavailableError) as exc_info:
        CsvSecurityPriceSource(missing_file, "manual")

    assert isinstance(exc_info.value.__cause__, CsvSecurityPriceUnavailableError)


def test_csv_source_corrupted_data_raises_corrupted_error(tmp_path: Path) -> None:
    corrupted_file = tmp_path / "corrupted.csv"
    corrupted_file.write_text("invalid,header,only\n1,2,3", encoding="utf-8")

    with pytest.raises(SecurityPriceCorruptedSourceDataError) as exc_info:
        CsvSecurityPriceSource(corrupted_file, "manual")

    assert isinstance(exc_info.value.__cause__, CsvSecurityPriceSourceError)
