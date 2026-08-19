"""Integration test verifying substitutability of FxRateSource adapters."""

from datetime import UTC, date, datetime
from pathlib import Path

from navlens import CurrencyCode, CurrencyPair, FxRate, FxRateKind, MarketDate
from navlens.datasets import (
    FxRateQuery,
    FxRateSnapshot,
    FxRateSource,
    select_fx_rate_snapshots,
)
from navlens.sources import CsvFxRateSource

SAMPLE_CSV = "\n".join(
    [
        "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at",
        # Initial observation for 2026-07-20 published at 15:30
        "test_source,USD,TRY,2026-07-20,34.0,non_cash_buying,2026-07-20T15:30:00Z,2026-07-20T15:35:00Z",
        # Revision observation for 2026-07-20 published at 17:00 (correction)
        "test_source,USD,TRY,2026-07-20,34.2,non_cash_buying,2026-07-20T17:00:00Z,2026-07-20T17:05:00Z",
        # Observation for 2026-07-21
        "test_source,USD,TRY,2026-07-21,34.5,non_cash_buying,2026-07-21T15:30:00Z,2026-07-21T15:35:00Z",
        "",
    ]
)


def _consumer_workflow(
    source: FxRateSource,
    pair: CurrencyPair,
    kind: FxRateKind,
    start_date: date,
    end_date: date,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> tuple[FxRateSnapshot, ...]:
    """Consumer retrieving candidates and delegating point-in-time selection."""
    query = FxRateQuery(
        pair=pair,
        kind=kind,
        start_date=start_date,
        end_date=end_date,
    )
    candidates = source.fetch_fx_rates(query)
    # The adapter returned all candidates without collapsing; consumer selects point-in-time winners
    return select_fx_rate_snapshots(
        candidates,
        source_id=source.source_id,
        pair=pair,
        kind=kind,
        at_timestamp=at_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )


def test_fx_rate_source_structural_substitutability_and_point_in_time_selection(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "rates.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    csv_source = CsvFxRateSource(csv_file, source_id="test_source")

    usd_try = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    # 1. Fetch raw candidates directly from the source to prove it does not collapse revisions
    raw_query = FxRateQuery(
        pair=usd_try,
        kind=kind,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
    )
    raw_candidates = csv_source.fetch_fx_rates(raw_query)
    assert len(raw_candidates) == 3
    assert [s.observation.rate for s in raw_candidates] == [
        FxRate(34.0),
        FxRate(34.2),
        FxRate(34.5),
    ]

    # 2. Execute consumer workflow before 17:00 correction -> initial revision (34.0) selected
    selected_before_correction = _consumer_workflow(
        source=csv_source,
        pair=usd_try,
        kind=kind,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
        at_timestamp=datetime(2026, 7, 20, 16, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 7, 21),
    )
    assert len(selected_before_correction) == 1
    assert selected_before_correction[0].observation.rate == FxRate(34.0)

    # 3. Execute consumer workflow after 17:00 correction -> revision (34.2) supersedes initial
    selected_after_correction = _consumer_workflow(
        source=csv_source,
        pair=usd_try,
        kind=kind,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
        at_timestamp=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 7, 21),
    )
    assert len(selected_after_correction) == 2
    assert [s.observation.rate for s in selected_after_correction] == [
        FxRate(34.2),
        FxRate(34.5),
    ]
