from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest
from navlens import (
    FundUnitPriceDatasetError,
    FundUnitPriceSnapshot,
    MarketDate,
    PriceObservation,
    UnitPrice,
    select_fund_unit_price_snapshots,
)


def _make_obs(
    date: MarketDate | None = None,
    price_val: float = 150.25,
) -> PriceObservation:
    date = date or MarketDate(2026, 1, 15)
    return PriceObservation(
        date,
        UnitPrice(price_val),
    )


def test_valid_immutable_fund_unit_price_snapshot() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    ing_time = datetime(2026, 1, 15, 18, 5, tzinfo=UTC)

    snapshot = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs,
        available_at=avail_time,
        ingested_at=ing_time,
        source_id="tefas",
    )

    assert snapshot.observation == obs
    assert snapshot.available_at == avail_time
    assert snapshot.ingested_at == ing_time
    assert snapshot.source_id == "tefas"
    assert snapshot.fund_id == "fund123"

    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.source_id = "reuters"  # type: ignore[misc]


def test_rejects_invalid_observation_type() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(FundUnitPriceDatasetError, match="observation"):
        FundUnitPriceSnapshot(
            fund_id="fund123",
            observation="not_an_observation",  # type: ignore[arg-type]
            available_at=avail_time,
            ingested_at=avail_time,
            source_id="tefas",
        )


@pytest.mark.parametrize("bad_source_id", ["", 123, None])
def test_rejects_empty_or_non_string_source_id(bad_source_id: str) -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(FundUnitPriceDatasetError, match="source_id"):
        FundUnitPriceSnapshot(
            fund_id="fund123",
            observation=obs,
            available_at=avail_time,
            ingested_at=avail_time,
            source_id=bad_source_id,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_fund_id", ["", 123, None])
def test_rejects_empty_or_non_string_fund_id(bad_fund_id: str) -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(FundUnitPriceDatasetError, match="fund_id"):
        FundUnitPriceSnapshot(
            fund_id=bad_fund_id,  # type: ignore[arg-type]
            observation=obs,
            available_at=avail_time,
            ingested_at=avail_time,
            source_id="tefas",
        )


def test_rejects_naive_and_non_utc_timestamps() -> None:
    obs = _make_obs()
    utc_dt = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    naive_dt = datetime(2026, 1, 15, 18, 0)
    non_utc_dt = datetime(2026, 1, 15, 18, 0, tzinfo=timezone(timedelta(hours=3)))

    with pytest.raises(FundUnitPriceDatasetError, match="timezone"):
        FundUnitPriceSnapshot(
            fund_id="fund123",
            observation=obs,
            available_at=naive_dt,
            ingested_at=utc_dt,
            source_id="tefas",
        )

    with pytest.raises(FundUnitPriceDatasetError, match="UTC"):
        FundUnitPriceSnapshot(
            fund_id="fund123",
            observation=obs,
            available_at=utc_dt,
            ingested_at=non_utc_dt,
            source_id="tefas",
        )


def test_rejects_ingestion_before_availability() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    earlier_ing = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)

    with pytest.raises(FundUnitPriceDatasetError, match="ingestion time cannot precede"):
        FundUnitPriceSnapshot(
            fund_id="fund123",
            observation=obs,
            available_at=avail_time,
            ingested_at=earlier_ing,
            source_id="tefas",
        )


def test_prevents_future_data_leakage() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    snapshot = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tefas",
    )

    before_avail = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)
    res = select_fund_unit_price_snapshots(
        [snapshot],
        source_id="tefas",
        fund_id="fund123",
        at_timestamp=before_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()

    at_avail = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    res_at = select_fund_unit_price_snapshots(
        [snapshot],
        source_id="tefas",
        fund_id="fund123",
        at_timestamp=at_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_at == (snapshot,)


def test_filters_by_pricing_as_of_date() -> None:
    obs_valid = _make_obs(date=MarketDate(2026, 1, 15))
    obs_future = _make_obs(date=MarketDate(2026, 1, 21))
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)

    snap_valid = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs_valid,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap_future = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs_future,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    res = select_fund_unit_price_snapshots(
        [snap_valid, snap_future],
        source_id="src1",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 22, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_valid,)


def test_correction_publication_timing_and_identity_superseding() -> None:
    date = MarketDate(2026, 1, 15)
    orig_obs = _make_obs(date=date, price_val=150.00)
    corr_obs = _make_obs(
        date=date,
        price_val=150.25,
    )

    orig_snapshot = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=orig_obs,
        available_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        source_id="tefas",
    )
    corr_snapshot = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=corr_obs,
        available_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        source_id="tefas",
    )

    snapshots = [orig_snapshot, corr_snapshot]

    res_before = select_fund_unit_price_snapshots(
        snapshots,
        source_id="tefas",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 15, 23, 59, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_before == (orig_snapshot,)

    res_after = select_fund_unit_price_snapshots(
        snapshots,
        source_id="tefas",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 16, 10, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_after == (corr_snapshot,)


def test_does_not_mix_different_sources() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)

    tefas_snap = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tefas",
    )
    reuters_snap = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="reuters",
    )

    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res_tefas = select_fund_unit_price_snapshots(
        [tefas_snap, reuters_snap],
        source_id="tefas",
        fund_id="fund123",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_tefas == (tefas_snap,)

    res_reuters = select_fund_unit_price_snapshots(
        [tefas_snap, reuters_snap],
        source_id="reuters",
        fund_id="fund123",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_reuters == (reuters_snap,)


def test_filters_by_fund_only() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)

    snap_target = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(
            date=date,
        ),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap_diff_fund = FundUnitPriceSnapshot(
        fund_id="fund456",
        observation=_make_obs(
            date=date,
        ),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    all_snaps = [snap_target, snap_diff_fund]
    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res = select_fund_unit_price_snapshots(
        all_snaps,
        source_id="src1",
        fund_id="fund123",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_target,)


def test_returns_chronological_tuple() -> None:
    avail_time = datetime(2026, 1, 20, 18, 0, tzinfo=UTC)

    snap1 = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=MarketDate(2026, 1, 15)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap2 = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=MarketDate(2026, 1, 16)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap3 = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=MarketDate(2026, 1, 17)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    res = select_fund_unit_price_snapshots(
        [snap3, snap1, snap2],
        source_id="src1",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )

    assert isinstance(res, tuple)
    assert res == (snap1, snap2, snap3)


def test_returns_empty_tuple_when_no_snapshots_match() -> None:
    res = select_fund_unit_price_snapshots(
        [],
        source_id="src1",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()
    assert isinstance(res, tuple)


def test_tied_timestamps_preserve_first_encountered() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)

    snap_first = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=date, price_val=100.0),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap_tied = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=date, price_val=105.0),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    res = select_fund_unit_price_snapshots(
        [snap_first, snap_tied],
        source_id="src1",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_first,)


def test_generator_input_materializes_safely() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date1 = MarketDate(2026, 1, 15)
    date2 = MarketDate(2026, 1, 16)

    snap1 = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=date1),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap2 = FundUnitPriceSnapshot(
        fund_id="fund123",
        observation=_make_obs(date=date2),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    def _yield_snaps() -> Iterator[FundUnitPriceSnapshot]:
        yield snap1
        yield snap2

    res = select_fund_unit_price_snapshots(
        _yield_snaps(),
        source_id="src1",
        fund_id="fund123",
        at_timestamp=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap1, snap2)
