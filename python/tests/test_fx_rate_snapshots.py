from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest
from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateDatasetError,
    FxRateKind,
    FxRateObservation,
    FxRateSnapshot,
    MarketDate,
    select_fx_rate_snapshots,
)


def _make_obs(
    base: str = "USD",
    quote: str = "TRY",
    date: MarketDate | None = None,
    rate_val: float = 35.25,
    kind_str: str = "non_cash_buying",
) -> FxRateObservation:
    date = date or MarketDate(2026, 1, 15)
    pair = CurrencyPair(CurrencyCode(base), CurrencyCode(quote))
    return FxRateObservation(
        pair,
        date,
        FxRate(rate_val),
        FxRateKind(kind_str),
    )


def test_valid_immutable_fx_rate_snapshot() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    ing_time = datetime(2026, 1, 15, 18, 5, tzinfo=UTC)

    snapshot = FxRateSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=ing_time,
        source_id="tcmb",
    )

    assert snapshot.observation == obs
    assert snapshot.available_at == avail_time
    assert snapshot.ingested_at == ing_time
    assert snapshot.source_id == "tcmb"

    with pytest.raises((FrozenInstanceError, AttributeError)):
        snapshot.source_id = "other_source"  # type: ignore[misc]


def test_rejects_invalid_observation_type() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(FxRateDatasetError, match="observation"):
        FxRateSnapshot(
            observation="not_an_observation",  # type: ignore[arg-type]
            available_at=avail_time,
            ingested_at=avail_time,
            source_id="tcmb",
        )


@pytest.mark.parametrize("bad_source_id", ["", 123, None])
def test_rejects_empty_or_non_string_source_id(bad_source_id: str) -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    with pytest.raises(FxRateDatasetError, match="source_id"):
        FxRateSnapshot(
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

    with pytest.raises(FxRateDatasetError, match="timezone"):
        FxRateSnapshot(
            observation=obs,
            available_at=naive_dt,
            ingested_at=utc_dt,
            source_id="tcmb",
        )

    with pytest.raises(FxRateDatasetError, match="UTC"):
        FxRateSnapshot(
            observation=obs,
            available_at=utc_dt,
            ingested_at=non_utc_dt,
            source_id="tcmb",
        )


def test_rejects_ingestion_before_availability() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    earlier_ing = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)

    with pytest.raises(FxRateDatasetError, match="ingestion time cannot precede"):
        FxRateSnapshot(
            observation=obs,
            available_at=avail_time,
            ingested_at=earlier_ing,
            source_id="tcmb",
        )


def test_prevents_future_data_leakage() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    snapshot = FxRateSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    before_avail = datetime(2026, 1, 15, 17, 59, tzinfo=UTC)
    res = select_fx_rate_snapshots(
        [snapshot],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=before_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()

    at_avail = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    res_at = select_fx_rate_snapshots(
        [snapshot],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=at_avail,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_at == (snapshot,)


def test_filters_by_pricing_as_of_date() -> None:
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    obs_valid = _make_obs(date=MarketDate(2026, 1, 15))
    obs_future = _make_obs(date=MarketDate(2026, 1, 21))
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)

    snap_valid = FxRateSnapshot(
        observation=obs_valid,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap_future = FxRateSnapshot(
        observation=obs_future,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    res = select_fx_rate_snapshots(
        [snap_valid, snap_future],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 22, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_valid,)


def test_correction_publication_timing_and_future_correction_exclusion() -> None:
    date = MarketDate(2026, 1, 15)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    orig_obs = _make_obs(date=date, rate_val=35.00)
    corr_obs = _make_obs(date=date, rate_val=35.25)

    orig_snapshot = FxRateSnapshot(
        observation=orig_obs,
        available_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
        source_id="tcmb",
    )
    corr_snapshot = FxRateSnapshot(
        observation=corr_obs,
        available_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        source_id="tcmb",
    )

    snapshots = [orig_snapshot, corr_snapshot]

    # Query before correction: original record is selected, future correction is excluded
    res_before = select_fx_rate_snapshots(
        snapshots,
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 15, 23, 59, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_before == (orig_snapshot,)

    # Query after correction: corrected record supersedes original
    res_after = select_fx_rate_snapshots(
        snapshots,
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 16, 10, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_after == (corr_snapshot,)


def test_does_not_mix_different_sources() -> None:
    obs = _make_obs()
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    tcmb_snap = FxRateSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    ecb_snap = FxRateSnapshot(
        observation=obs,
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="ecb",
    )

    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res_tcmb = select_fx_rate_snapshots(
        [tcmb_snap, ecb_snap],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_tcmb == (tcmb_snap,)

    res_ecb = select_fx_rate_snapshots(
        [tcmb_snap, ecb_snap],
        source_id="ecb",
        pair=usd_try,
        kind=kind,
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_ecb == (ecb_snap,)


def test_pair_and_directional_pair_isolation() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)
    kind = FxRateKind("non_cash_buying")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    try_usd = CurrencyPair(CurrencyCode("TRY"), CurrencyCode("USD"))
    eur_try = CurrencyPair(CurrencyCode("EUR"), CurrencyCode("TRY"))

    snap_usd_try = FxRateSnapshot(
        observation=_make_obs(base="USD", quote="TRY", date=date),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap_try_usd = FxRateSnapshot(
        observation=_make_obs(base="TRY", quote="USD", date=date),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap_eur_try = FxRateSnapshot(
        observation=_make_obs(base="EUR", quote="TRY", date=date),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    all_snaps = [snap_usd_try, snap_try_usd, snap_eur_try]
    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    # Directional check: USD/TRY should not match TRY/USD or EUR/TRY
    res_usd_try = select_fx_rate_snapshots(
        all_snaps,
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_usd_try == (snap_usd_try,)

    res_try_usd = select_fx_rate_snapshots(
        all_snaps,
        source_id="tcmb",
        pair=try_usd,
        kind=kind,
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_try_usd == (snap_try_usd,)

    res_eur_try = select_fx_rate_snapshots(
        all_snaps,
        source_id="tcmb",
        pair=eur_try,
        kind=kind,
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_eur_try == (snap_eur_try,)


def test_exact_fx_rate_kind_isolation() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))

    snap_non_cash = FxRateSnapshot(
        observation=_make_obs(date=date, kind_str="non_cash_buying"),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap_cash = FxRateSnapshot(
        observation=_make_obs(date=date, kind_str="cash_buying"),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    all_snaps = [snap_non_cash, snap_cash]
    query_time = datetime(2026, 1, 16, 0, 0, tzinfo=UTC)

    res_non_cash = select_fx_rate_snapshots(
        all_snaps,
        source_id="tcmb",
        pair=usd_try,
        kind=FxRateKind("non_cash_buying"),
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_non_cash == (snap_non_cash,)

    res_cash = select_fx_rate_snapshots(
        all_snaps,
        source_id="tcmb",
        pair=usd_try,
        kind=FxRateKind("cash_buying"),
        at_timestamp=query_time,
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res_cash == (snap_cash,)


def test_returns_chronological_tuple() -> None:
    avail_time = datetime(2026, 1, 20, 18, 0, tzinfo=UTC)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    snap1 = FxRateSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 15)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap2 = FxRateSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 16)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap3 = FxRateSnapshot(
        observation=_make_obs(date=MarketDate(2026, 1, 17)),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    # Pass unordered list [snap3, snap1, snap2]
    res = select_fx_rate_snapshots(
        [snap3, snap1, snap2],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )

    assert isinstance(res, tuple)
    assert res == (snap1, snap2, snap3)


def test_returns_empty_tuple_when_no_snapshots_match() -> None:
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    res = select_fx_rate_snapshots(
        [],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 21, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == ()
    assert isinstance(res, tuple)


def test_tied_timestamps_preserve_first_encountered() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date = MarketDate(2026, 1, 15)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    snap_first = FxRateSnapshot(
        observation=_make_obs(date=date, rate_val=35.0),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap_tied = FxRateSnapshot(
        observation=_make_obs(date=date, rate_val=35.5),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    res = select_fx_rate_snapshots(
        [snap_first, snap_tied],
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap_first,)


def test_generator_input_consumed_once() -> None:
    avail_time = datetime(2026, 1, 15, 18, 0, tzinfo=UTC)
    date1 = MarketDate(2026, 1, 15)
    date2 = MarketDate(2026, 1, 16)
    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    snap1 = FxRateSnapshot(
        observation=_make_obs(date=date1),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )
    snap2 = FxRateSnapshot(
        observation=_make_obs(date=date2),
        available_at=avail_time,
        ingested_at=avail_time,
        source_id="tcmb",
    )

    def _yield_snaps():
        yield snap1
        yield snap2

    res = select_fx_rate_snapshots(
        _yield_snaps(),
        source_id="tcmb",
        pair=usd_try,
        kind=kind,
        at_timestamp=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 1, 20),
    )
    assert res == (snap1, snap2)
