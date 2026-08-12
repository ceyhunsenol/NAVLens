from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from navlens import FundUnitPriceDatasetError
from navlens.sources.tefas import (
    TEFAS_SOURCE_ID,
    TefasAcquisitionResult,
    TefasPriceRecord,
    to_fund_unit_price_snapshots,
)


def _acquisition() -> TefasAcquisitionResult:
    return TefasAcquisitionResult(
        (
            TefasPriceRecord(date(2026, 8, 10), "AAL", 1.0),
            TefasPriceRecord(date(2026, 8, 11), "AAL", 1.01),
        ),
        Path("raw.json"),
        False,
    )


def test_maps_acquired_records_to_conservative_point_in_time_snapshots() -> None:
    acquired_at = datetime(2026, 8, 12, 12, tzinfo=UTC)

    snapshots = to_fund_unit_price_snapshots(_acquisition(), acquired_at=acquired_at)

    assert [str(snapshot.observation.date) for snapshot in snapshots] == [
        "2026-08-10",
        "2026-08-11",
    ]
    assert all(snapshot.fund_id == "AAL" for snapshot in snapshots)
    assert all(snapshot.source_id == TEFAS_SOURCE_ID for snapshot in snapshots)
    assert all(snapshot.available_at is acquired_at for snapshot in snapshots)
    assert all(snapshot.ingested_at is acquired_at for snapshot in snapshots)


def test_rejects_non_utc_acquisition_timestamp() -> None:
    non_utc = datetime(2026, 8, 12, 15, tzinfo=timezone(timedelta(hours=3)))

    with pytest.raises(FundUnitPriceDatasetError, match="UTC"):
        to_fund_unit_price_snapshots(_acquisition(), acquired_at=non_utc)
