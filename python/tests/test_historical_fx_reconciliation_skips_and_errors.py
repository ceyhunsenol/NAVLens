"""Tests for skips, revision filtering, and validation errors in historical FX reconciliation."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from navlens import MarketDate, ReturnPeriod
from navlens.reconciliation.historical import (
    DecreasingPeriodError,
    DuplicatePeriodError,
    HistoricalFxReconciliationRecord,
    InvalidHistoricalReconciliationRequestError,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedFxReconciliationRecord,
    build_historical_fx_reconciliation_dataset,
)
from tests.historical_fx_reconciliation_fixtures import (
    make_fund_price_snap,
    make_fx_rate_snap,
    make_fx_request,
    make_holding_snap,
    make_security_price_snap,
)


def test_rejects_duplicate_or_decreasing_periods() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    tz2 = datetime(2026, 1, 3, 10, tzinfo=UTC)

    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 3))

    req1 = make_fx_request(MarketDate(2026, 1, 3), tz1, p1)
    req_dup = make_fx_request(MarketDate(2026, 1, 3), tz2, p1)

    with pytest.raises(DuplicatePeriodError):
        build_historical_fx_reconciliation_dataset(
            [req1, req_dup],
            [],
            [],
            [],
            [],
        )

    p2_early = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req_dec = make_fx_request(MarketDate(2026, 1, 2), tz2, p2_early)

    with pytest.raises(DecreasingPeriodError):
        build_historical_fx_reconciliation_dataset(
            [req1, req_dec],
            [],
            [],
            [],
            [],
        )


def test_skips_on_missing_holdings_or_fund_prices() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    req = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)

    # Missing holdings
    dataset_no_holdings = build_historical_fx_reconciliation_dataset(
        [req],
        [],
        [
            make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
            make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
        ],
        [],
        [
            make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
            make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, tz1),
        ],
    )
    assert len(dataset_no_holdings.outcomes) == 1
    record_no_h = dataset_no_holdings.outcomes[0]
    assert isinstance(record_no_h, SkippedFxReconciliationRecord)
    assert isinstance(record_no_h.reason, MissingHoldingsSkip)

    # Missing end fund price
    dataset_no_fp = build_historical_fx_reconciliation_dataset(
        [req],
        [make_holding_snap(MarketDate(2026, 1, 1), tz1)],
        [
            make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
            make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
        ],
        [],
        [make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1)],
    )
    assert len(dataset_no_fp.outcomes) == 1
    record_no_fp = dataset_no_fp.outcomes[0]
    assert isinstance(record_no_fp, SkippedFxReconciliationRecord)
    assert isinstance(record_no_fp.reason, MissingFundPriceSkip)
    assert record_no_fp.reason.required_date == MarketDate(2026, 1, 2)

    dataset_no_start = build_historical_fx_reconciliation_dataset(
        [req],
        [make_holding_snap(MarketDate(2026, 1, 1), tz1)],
        [
            make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
            make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
        ],
        [],
        [make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, tz1)],
    )
    record_no_start = dataset_no_start.outcomes[0]
    assert isinstance(record_no_start, SkippedFxReconciliationRecord)
    assert isinstance(record_no_start.reason, MissingFundPriceSkip)
    assert record_no_start.reason.required_date == MarketDate(2026, 1, 1)


def test_filters_future_holdings_and_fund_price_revisions() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    tz_future = datetime(2026, 1, 2, 12, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))

    req = make_fx_request(MarketDate(2026, 1, 2), tz1, p1)

    # Future holdings snapshot published after prediction_timestamp
    future_holdings = [make_holding_snap(MarketDate(2026, 1, 1), tz_future)]
    ds_h = build_historical_fx_reconciliation_dataset(
        [req],
        future_holdings,
        [],
        [],
        [],
    )
    assert isinstance(ds_h.outcomes[0], SkippedFxReconciliationRecord)

    # Future fund price published after prediction_timestamp
    future_fund_prices = [
        make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, tz1),
        make_fund_price_snap(MarketDate(2026, 1, 2), 10.5, tz_future),
    ]
    ds_fp = build_historical_fx_reconciliation_dataset(
        [req],
        [make_holding_snap(MarketDate(2026, 1, 1), tz1)],
        [
            make_security_price_snap(MarketDate(2026, 1, 1), 100.0, tz1),
            make_security_price_snap(MarketDate(2026, 1, 2), 105.0, tz1),
        ],
        [],
        future_fund_prices,
    )
    assert isinstance(ds_fp.outcomes[0], SkippedFxReconciliationRecord)


def test_filters_future_security_price_and_fx_revisions() -> None:
    prediction_time = datetime(2026, 1, 2, 10, tzinfo=UTC)
    future_time = datetime(2026, 1, 2, 12, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    request = make_fx_request(MarketDate(2026, 1, 2), prediction_time, period)

    visible_end_price = make_security_price_snap(MarketDate(2026, 1, 2), 105.0, prediction_time)
    future_end_price = make_security_price_snap(MarketDate(2026, 1, 2), 999.0, future_time)
    visible_end_fx = make_fx_rate_snap(MarketDate(2026, 1, 2), 31.0, prediction_time)
    future_end_fx = make_fx_rate_snap(MarketDate(2026, 1, 2), 99.0, future_time)

    dataset = build_historical_fx_reconciliation_dataset(
        [request],
        [make_holding_snap(MarketDate(2026, 1, 1), prediction_time)],
        [
            make_security_price_snap(MarketDate(2026, 1, 1), 100.0, prediction_time),
            visible_end_price,
            future_end_price,
        ],
        [
            make_fx_rate_snap(MarketDate(2026, 1, 1), 30.0, prediction_time),
            visible_end_fx,
            future_end_fx,
        ],
        [
            make_fund_price_snap(MarketDate(2026, 1, 1), 10.0, prediction_time),
            make_fund_price_snap(MarketDate(2026, 1, 2), 10.845, prediction_time),
        ],
    )

    record = dataset.outcomes[0]
    assert isinstance(record, HistoricalFxReconciliationRecord)
    selected_prices = record.result.contribution.request.alignment_result.selected_price_snapshots
    assert visible_end_price in selected_prices
    assert future_end_price not in selected_prices
    assert visible_end_fx in record.result.contribution.selected_fx_snapshots
    assert future_end_fx not in record.result.contribution.selected_fx_snapshots


def test_invalid_request_fails_fast() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    p1 = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))

    with pytest.raises(InvalidHistoricalReconciliationRequestError):
        make_fx_request(MarketDate(2026, 1, 2), tz1, p1, fund_price_source_id="")

    with pytest.raises(InvalidHistoricalReconciliationRequestError):
        make_fx_request(MarketDate(2026, 1, 2), tz1, p1, fx_source_id="")


def test_unrelated_orchestration_errors_fail_fast() -> None:
    prediction_time = datetime(2026, 1, 2, 10, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    request = make_fx_request(MarketDate(2026, 1, 2), prediction_time, period)

    with (
        patch(
            "navlens.reconciliation.historical.fx_builder.align_point_in_time",
            side_effect=RuntimeError("unexpected failure"),
        ),
        pytest.raises(RuntimeError, match="unexpected failure"),
    ):
        build_historical_fx_reconciliation_dataset([request], [], [], [], [])
