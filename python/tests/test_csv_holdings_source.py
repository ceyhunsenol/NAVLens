from datetime import UTC, datetime
from pathlib import Path

import pytest
from navlens import AssetClass, MarketDate, read_holdings_snapshots
from navlens.sources import CsvHoldingsSourceError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parses_single_snapshot_csv() -> None:
    path = FIXTURES_DIR / "holdings_single.csv"
    snapshots = read_holdings_snapshots(path)

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.fund_id == "AAL"
    assert snapshot.effective_date == MarketDate(2026, 1, 31)
    assert snapshot.published_at == datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    assert snapshot.ingested_at == datetime(2026, 2, 5, 10, 5, tzinfo=UTC)
    assert snapshot.source_id == "kap_report"
    assert len(snapshot.positions) == 2

    pos0 = snapshot.positions[0]
    assert pos0.instrument_id == "US67066G1040"
    assert pos0.asset_class == AssetClass("equity")
    assert pos0.fund_total_weight == pytest.approx(0.0544)

    pos1 = snapshot.positions[1]
    assert pos1.instrument_id == "US5949181045"
    assert pos1.asset_class == AssetClass("equity")
    assert pos1.fund_total_weight == pytest.approx(0.0456)


def test_parses_mixed_metadata_csv() -> None:
    path = FIXTURES_DIR / "holdings_mixed.csv"
    snapshots = read_holdings_snapshots(path)

    assert len(snapshots) == 3

    # First snapshot: AAL 2026-01-31
    assert snapshots[0].fund_id == "AAL"
    assert snapshots[0].effective_date == MarketDate(2026, 1, 31)
    assert snapshots[0].source_id == "kap_jan"
    assert len(snapshots[0].positions) == 1

    # Second snapshot: AAL 2026-02-28
    assert snapshots[1].fund_id == "AAL"
    assert snapshots[1].effective_date == MarketDate(2026, 2, 28)
    assert snapshots[1].source_id == "kap_feb"
    assert len(snapshots[1].positions) == 1

    # Third snapshot: XYZ 2026-02-28
    assert snapshots[2].fund_id == "XYZ"
    assert snapshots[2].effective_date == MarketDate(2026, 2, 28)
    assert snapshots[2].source_id == "kap_feb"
    assert len(snapshots[2].positions) == 1
    assert snapshots[2].positions[0].asset_class == AssetClass("debt_security")


def test_rejects_non_existent_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"
    with pytest.raises(CsvHoldingsSourceError, match="cannot read CSV file"):
        read_holdings_snapshots(missing_path)


def test_rejects_empty_csv(tmp_path: Path) -> None:
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")
    with pytest.raises(CsvHoldingsSourceError, match="missing"):
        read_holdings_snapshots(empty_path)


def test_rejects_missing_required_columns(tmp_path: Path) -> None:
    path = tmp_path / "missing_cols.csv"
    path.write_text("fund_id,effective_date,weight\n", encoding="utf-8")
    with pytest.raises(CsvHoldingsSourceError, match="missing required columns"):
        read_holdings_snapshots(path)


def test_rejects_missing_field_values(tmp_path: Path) -> None:
    path = tmp_path / "missing_val.csv"
    path.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "AAL,2026-01-31,,2026-02-05T10:05:00Z,kap_report,US67066G1040,equity,0.0544\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvHoldingsSourceError, match="published_at is required"):
        read_holdings_snapshots(path)


def test_rejects_invalid_dates_and_timestamps(tmp_path: Path) -> None:
    # Invalid date
    bad_date = tmp_path / "bad_date.csv"
    bad_date.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "AAL,2026-02-31,2026-02-05T10:00:00Z,2026-02-05T10:05:00Z,kap_report,US67066G1040,equity,0.0544\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvHoldingsSourceError, match="invalid ISO date"):
        read_holdings_snapshots(bad_date)

    # Naive timestamp without timezone
    naive_ts = tmp_path / "naive_ts.csv"
    naive_ts.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "AAL,2026-01-31,2026-02-05 10:00:00,2026-02-05T10:05:00Z,"
        "kap_report,US67066G1040,equity,0.0544\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvHoldingsSourceError, match="timezone"):
        read_holdings_snapshots(naive_ts)


def test_rejects_invalid_asset_classes_and_weights(tmp_path: Path) -> None:
    # Invalid asset class string
    bad_ac = tmp_path / "bad_ac.csv"
    bad_ac.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "AAL,2026-01-31,2026-02-05T10:00:00Z,2026-02-05T10:05:00Z,kap_report,US67066G1040,stock,0.0544\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvHoldingsSourceError, match="invalid asset_class"):
        read_holdings_snapshots(bad_ac)

    # Weight out of range
    bad_weight = tmp_path / "bad_weight.csv"
    bad_weight.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "AAL,2026-01-31,2026-02-05T10:00:00Z,2026-02-05T10:05:00Z,kap_report,US67066G1040,equity,1.5\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvHoldingsSourceError, match="weight"):
        read_holdings_snapshots(bad_weight)
