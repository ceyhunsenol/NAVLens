from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest
from navlens import (
    AssetClass,
    HoldingDatasetError,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    select_latest_holdings_snapshot,
)


def _make_position(instrument_id: str = "US67066G1040", weight: float = 0.05) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def test_valid_immutable_snapshot() -> None:
    pub_time = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    ing_time = datetime(2026, 2, 5, 10, 5, tzinfo=UTC)
    pos = _make_position()

    snapshot = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=pub_time,
        ingested_at=ing_time,
        source_id="kap_report",
        positions=(pos,),
    )

    assert snapshot.fund_id == "AAL"
    assert snapshot.effective_date == MarketDate(2026, 1, 31)
    assert snapshot.published_at == pub_time
    assert snapshot.ingested_at == ing_time
    assert snapshot.source_id == "kap_report"
    assert snapshot.positions == (pos,)
    assert isinstance(snapshot.positions, tuple)

    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.fund_id = "OTHER"  # type: ignore[misc]


def test_rejects_empty_positions() -> None:
    pub_time = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    ing_time = datetime(2026, 2, 5, 10, 5, tzinfo=UTC)

    with pytest.raises(HoldingDatasetError, match="empty"):
        HoldingSnapshot(
            fund_id="AAL",
            effective_date=MarketDate(2026, 1, 31),
            published_at=pub_time,
            ingested_at=ing_time,
            source_id="kap_report",
            positions=(),
        )


def test_rejects_naive_or_non_utc_timestamps() -> None:
    pub_utc = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    naive_dt = datetime(2026, 2, 5, 10, 0)
    non_utc_dt = datetime(2026, 2, 5, 10, 0, tzinfo=timezone(timedelta(hours=3)))
    pos = _make_position()

    with pytest.raises(HoldingDatasetError, match="timezone"):
        HoldingSnapshot(
            fund_id="AAL",
            effective_date=MarketDate(2026, 1, 31),
            published_at=naive_dt,
            ingested_at=pub_utc,
            source_id="kap_report",
            positions=(pos,),
        )

    with pytest.raises(HoldingDatasetError, match="UTC"):
        HoldingSnapshot(
            fund_id="AAL",
            effective_date=MarketDate(2026, 1, 31),
            published_at=pub_utc,
            ingested_at=non_utc_dt,
            source_id="kap_report",
            positions=(pos,),
        )


def test_rejects_ingestion_before_publication() -> None:
    pub_time = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    earlier_ing = datetime(2026, 2, 5, 9, 59, tzinfo=UTC)
    pos = _make_position()

    with pytest.raises(HoldingDatasetError, match="ingestion time cannot precede publication time"):
        HoldingSnapshot(
            fund_id="AAL",
            effective_date=MarketDate(2026, 1, 31),
            published_at=pub_time,
            ingested_at=earlier_ing,
            source_id="kap_report",
            positions=(pos,),
        )


def test_prevents_future_data_leakage() -> None:
    pub_time = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    snapshot = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=pub_time,
        ingested_at=pub_time,
        source_id="kap_report",
        positions=(_make_position(),),
    )

    before_pub = datetime(2026, 2, 5, 9, 59, tzinfo=UTC)
    selected = select_latest_holdings_snapshot([snapshot], "AAL", at_timestamp=before_pub)
    assert selected is None

    at_pub = datetime(2026, 2, 5, 10, 0, tzinfo=UTC)
    selected_at_pub = select_latest_holdings_snapshot([snapshot], "AAL", at_timestamp=at_pub)
    assert selected_at_pub == snapshot


def test_selects_newest_effective_period() -> None:
    jan_snapshot = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        source_id="kap_jan",
        positions=(_make_position("JAN_POS"),),
    )
    feb_snapshot = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 2, 28),
        published_at=datetime(2026, 3, 5, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 3, 5, 10, 0, tzinfo=UTC),
        source_id="kap_feb",
        positions=(_make_position("FEB_POS"),),
    )

    query_time = datetime(2026, 3, 6, 0, 0, tzinfo=UTC)
    selected = select_latest_holdings_snapshot(
        [jan_snapshot, feb_snapshot], "AAL", at_timestamp=query_time
    )
    assert selected == feb_snapshot


def test_correction_publication_timing() -> None:
    original = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        source_id="kap_original",
        positions=(_make_position("ORIGINAL"),),
    )
    correction = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        source_id="kap_correction",
        positions=(_make_position("CORRECTION"),),
    )

    snapshots = [original, correction]

    # Before correction publication: original is selected
    before_correction = datetime(2026, 2, 6, 0, 0, tzinfo=UTC)
    res_before = select_latest_holdings_snapshot(snapshots, "AAL", at_timestamp=before_correction)
    assert res_before == original

    # After correction publication: correction supersedes original
    after_correction = datetime(2026, 2, 11, 0, 0, tzinfo=UTC)
    res_after = select_latest_holdings_snapshot(snapshots, "AAL", at_timestamp=after_correction)
    assert res_after == correction


def test_ignores_snapshots_of_other_funds() -> None:
    aal_snapshot = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        source_id="kap_aal",
        positions=(_make_position("AAL_POS"),),
    )
    xyz_snapshot = HoldingSnapshot(
        fund_id="XYZ",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 5, 10, 0, tzinfo=UTC),
        source_id="kap_xyz",
        positions=(_make_position("XYZ_POS"),),
    )

    query_time = datetime(2026, 2, 6, 0, 0, tzinfo=UTC)
    res_aal = select_latest_holdings_snapshot(
        [aal_snapshot, xyz_snapshot], "AAL", at_timestamp=query_time
    )
    assert res_aal == aal_snapshot

    res_xyz = select_latest_holdings_snapshot(
        [aal_snapshot, xyz_snapshot], "XYZ", at_timestamp=query_time
    )
    assert res_xyz == xyz_snapshot


def test_returns_none_when_no_snapshot_available() -> None:
    query_time = datetime(2026, 2, 6, 0, 0, tzinfo=UTC)
    assert select_latest_holdings_snapshot([], "AAL", at_timestamp=query_time) is None
