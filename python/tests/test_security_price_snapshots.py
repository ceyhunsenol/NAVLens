from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest
from navlens import (
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    SecurityPriceDatasetError,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    select_security_price_snapshots,
)


def _make_obs(
    instrument_id: str = "US67066G1040",
    date: MarketDate | None = None,
    price_val: float = 150.25,
    currency_code: str = "USD",
    adjustment_str: str = "unadjusted",
) -> SecurityPriceObservation:
    date = date or MarketDate(2026, 1, 15)
    return SecurityPriceObservation(
        instrument_id,
        date,
        UnitPrice(price_val),
        CurrencyCode(currency_code),
        PriceAdjustment(adjustment_str),
    )


def test_valid_immutable_security_price_snapshot() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    ing_time = datetime(2026, 1, 15, 18, 5, tzinfo=UTC)

    snapshot = SecurityPriceSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=ing_time,
        source_id="bloomberg",
    )

    assert snapshot.observation == obs
    assert snapshot.available_at == avail_time
    assert snapshot.ingested_at == ing_time
    assert snapshot.source_id == "bloomberg"

    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.source_id = "reuters"  # type: ignore[misc]


def test_rejects_invalid_observation_type() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(SecurityPriceDatasetError, match="observation"):
        SecurityPriceSnapshot(
            observation="not_an_observation",  # type: ignore[arg-type]
            available_at=avail_time,
            ingested_at=avail_time,
            source_id="bloomberg",
        )


@pytest.mark.parametrize("bad_source_id", ["", 123, None])
def test_rejects_empty_or_non_string_source_id(bad_source_id: str) -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(SecurityPriceDatasetError, match="source_id"):
        SecurityPriceSnapshot(
            observation=obs,
            available_at=avail_time,
            ingested_at=avail_time,
            source_id=bad_source_id,  # type: ignore[arg-type]
        )


def test_rejects_naive_and_non_utc_timestamps() -> None:
    obs = _make_obs()
    utc_dt = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    naive_dt = datetime(2026, 1, 15, 18, 0)
    non_utc_dt = datetime(2026, 1, 15, 18, 0, tzinfo=timezone(timedelta(hours=3)))

    with pytest.raises(SecurityPriceDatasetError, match="timezone"):
        SecurityPriceSnapshot(
            observation=obs,
            available_at=naive_dt,
            ingested_at=utc_dt,
            source_id="bloomberg",
        )

    with pytest.raises(SecurityPriceDatasetError, match="UTC"):
        SecurityPriceSnapshot(
            observation=obs,
            available_at=utc_dt,
            ingested_at=non_utc_dt,
            source_id="bloomberg",
        )


def test_rejects_ingestion_before_availability() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    earlier_ing = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)

    with pytest.raises(SecurityPriceDatasetError, match="ingestion time cannot precede"):
        SecurityPriceSnapshot(
            observation=obs,
            available_at=avail_time,
            ingested_at=earlier_ing,
            source_id="bloomberg",
        )


def test_prevents_future_data_leakage() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    snapshot = SecurityPriceSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="bloomberg",
    )

    before_avail = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)
    res = select_security_price_snapshots(
        [snapshot],
        source_id="bloomberg",
        instrument_id="US67066G1040",
        at_timestamp=before_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()

    at_avail = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    res_at = select_security_price_snapshots(
        [snapshot],
        source_id="bloomberg",
        instrument_id="US67066G1040",
        at_timestamp=at_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_at == (snapshot,)


def test_filters_by_pricing_as_of_date() -> None:
    obs_valid = _make_obs(date=MarketDate(2026, 1, 15))
    obs_future = _make_obs(date=MarketDate(2026, 1, 21))
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)

    snap_valid = SecurityPriceSnapshot(
        observation=obs_valid, available_at=avail_time, ingested_at=avail_time, source_id="src1"
    )
    snap_future = SecurityPriceSnapshot(
        observation=obs_future, available_at=avail_time, ingested_at=avail_time, source_id="src1"
    )

    res = select_security_price_snapshots(
        [snap_valid, snap_future],
        source_id="src1",
        instrument_id="US67066G1040",
        at_timestamp=datetime(2026, 1, 22, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_valid,)


@pytest.mark.parametrize(
    ("corrected_currency", "corrected_adjustment"),
    [("TRY", "unadjusted"), ("USD", "split_adjusted")],
)
def test_correction_publication_timing_and_identity_superseding(
    corrected_currency: str,
    corrected_adjustment: str,
) -> None:
    date = MarketDate(2026, 1, 15)
    orig_obs = _make_obs(date=date, price_val=150.00, currency_code="USD")
    corr_obs = _make_obs(
        date=date,
        price_val=150.25,
        currency_code=corrected_currency,
        adjustment_str=corrected_adjustment,
    )

    orig_snapshot = SecurityPriceSnapshot(
        observation=orig_obs,
        available_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        source_id="bloomberg",
    )
    corr_snapshot = SecurityPriceSnapshot(
        observation=corr_obs,
        available_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        source_id="bloomberg",
    )

    snapshots = [orig_snapshot, corr_snapshot]

    # Query before correction: original record is selected
    res_before = select_security_price_snapshots(
        snapshots,
        source_id="bloomberg",
        instrument_id="US67066G1040",
        at_timestamp=datetime(2026, 1, 15, 23, 59, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_before == (orig_snapshot,)

    # Query after correction: corrected record is selected (superseding currency change)
    res_after = select_security_price_snapshots(
        snapshots,
        source_id="bloomberg",
        instrument_id="US67066G1040",
        at_timestamp=datetime(2026, 1, 16, 10, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_after == (corr_snapshot,)


def test_does_not_mix_different_sources() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)

    bloomberg_snap = SecurityPriceSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="bloomberg",
    )
    reuters_snap = SecurityPriceSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="reuters",
    )

    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res_bloomberg = select_security_price_snapshots(
        [bloomberg_snap, reuters_snap],
        source_id="bloomberg",
        instrument_id="US67066G1040",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_bloomberg == (bloomberg_snap,)

    res_reuters = select_security_price_snapshots(
        [bloomberg_snap, reuters_snap],
        source_id="reuters",
        instrument_id="US67066G1040",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_reuters == (reuters_snap,)


def test_filters_by_instrument_only() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)

    snap_target = SecurityPriceSnapshot(
        observation=_make_obs(
            instrument_id="US67066G1040",
            date=date,
            currency_code="USD",
            adjustment_str="unadjusted",
        ),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap_diff_inst = SecurityPriceSnapshot(
        observation=_make_obs(
            instrument_id="US0378331005",
            date=date,
            currency_code="USD",
            adjustment_str="unadjusted",
        ),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    all_snaps = [snap_target, snap_diff_inst]
    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res = select_security_price_snapshots(
        all_snaps,
        source_id="src1",
        instrument_id="US67066G1040",
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_target,)


def test_returns_chronological_tuple() -> None:
    avail_time = datetime(2026, 1, 20, 18, 0, tzinfo=UTC)

    snap1 = SecurityPriceSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 15)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap2 = SecurityPriceSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 16)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )
    snap3 = SecurityPriceSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 17)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="src1",
    )

    # Pass unordered list [snap3, snap1, snap2]
    res = select_security_price_snapshots(
        [snap3, snap1, snap2],
        source_id="src1",
        instrument_id="US67066G1040",
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )

    assert isinstance(res, tuple)
    assert res == (snap1, snap2, snap3)


def test_returns_empty_tuple_when_no_snapshots_match() -> None:
    res = select_security_price_snapshots(
        [],
        source_id="src1",
        instrument_id="US67066G1040",
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()
    assert isinstance(res, tuple)
