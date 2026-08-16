"""Integration tests for historical reconciliation dataset builder."""

import typing
from datetime import UTC, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    MarketDate,
    PriceAdjustment,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    UnitPrice,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import (
    FundUnitPriceSnapshot,
    HoldingSnapshot,
    SecurityPriceSnapshot,
)
from navlens.reconciliation.historical import (
    DecreasingPeriodError,
    DuplicatePeriodError,
    HistoricalReconciliationRecord,
    HistoricalReconciliationRequest,
    InvalidHistoricalReconciliationRequestError,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
    build_historical_reconciliation_dataset,
)


def _make_alignment_req(date: MarketDate, tz: datetime) -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=tz,
        policy=AlignmentPolicy(
            CurrencyCode("TRY"),
            PriceAdjustment("unadjusted"),
            date,
            minimum_observations=2,
            max_staleness_calendar_days=5,
        ),
    )


def _make_holding_snap(date: MarketDate, published_at: datetime) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id="TEST_FUND",
        effective_date=date,
        published_at=published_at,
        ingested_at=published_at,
        source_id="src_h",
        positions=(HoldingPosition("INST_A", AssetClass("equity"), 1.0),),
    )


def _make_security_price(
    date: MarketDate, price: float, available_at: datetime
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            "INST_A",
            date,
            UnitPrice(price),
            CurrencyCode("TRY"),
            PriceAdjustment("unadjusted"),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="src_p",
    )


def _make_fund_price(
    date: MarketDate, price: float, available_at: datetime
) -> FundUnitPriceSnapshot:
    return FundUnitPriceSnapshot(
        fund_id="TEST_FUND",
        observation=PriceObservation(
            date,
            UnitPrice(price),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="src_f",
    )


def test_builds_consecutive_records_successfully() -> None:
    tz1 = datetime(2026, 1, 2, 10, tzinfo=UTC)
    tz2 = datetime(2026, 1, 3, 10, tzinfo=UTC)

    req1 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 2), tz1),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    req2 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 3), tz2),
        period=ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3)),
        fund_price_source_id="src_f",
    )

    holdings = [
        _make_holding_snap(MarketDate(2026, 1, 1), tz1),
        _make_holding_snap(MarketDate(2026, 1, 2), tz2),
    ]
    prices = [
        _make_security_price(MarketDate(2026, 1, 1), 10.0, tz1),
        _make_security_price(MarketDate(2026, 1, 2), 11.0, tz1),
        _make_security_price(MarketDate(2026, 1, 3), 12.1, tz2),
    ]
    fund_prices = [
        _make_fund_price(MarketDate(2026, 1, 1), 100.0, tz1),
        _make_fund_price(MarketDate(2026, 1, 2), 110.0, tz1),
        _make_fund_price(MarketDate(2026, 1, 3), 121.0, tz2),
    ]

    dataset = build_historical_reconciliation_dataset(
        (r for r in [req1, req2]),
        (h for h in holdings),
        (p for p in prices),
        (fp for fp in fund_prices),
    )

    assert len(dataset.outcomes) == 2
    rec1 = dataset.outcomes[0]
    rec2 = dataset.outcomes[1]

    assert isinstance(rec1, HistoricalReconciliationRecord)
    assert isinstance(rec2, HistoricalReconciliationRecord)

    assert rec1.request is req1
    assert rec2.request is req2

    assert rec1.result.start_snapshot is fund_prices[0]
    assert rec1.result.end_snapshot is fund_prices[1]
    assert rec2.result.start_snapshot is fund_prices[1]
    assert rec2.result.end_snapshot is fund_prices[2]
    assert rec1.result.contribution.alignment_result.holdings_snapshot is holdings[0]
    assert rec2.result.contribution.alignment_result.holdings_snapshot is holdings[1]
    assert rec1.return_coverage == 1.0
    assert rec2.return_coverage == 1.0
    assert rec1.observed_portfolio_contribution == pytest.approx(0.1)
    assert rec2.observed_portfolio_contribution == pytest.approx(0.1)
    assert rec1.reconciliation_residual == pytest.approx(0.0)
    assert rec2.reconciliation_residual == pytest.approx(0.0)


def test_prevents_future_leakage() -> None:
    # A correction is published at tz_correction
    tz_initial = datetime(2026, 1, 2, 10, tzinfo=UTC)
    tz_correction = datetime(2026, 1, 5, 10, tzinfo=UTC)

    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz_initial),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )

    holdings = [_make_holding_snap(MarketDate(2026, 1, 1), tz_initial)]
    prices = [
        _make_security_price(MarketDate(2026, 1, 1), 10.0, tz_initial),
        _make_security_price(MarketDate(2026, 1, 2), 11.0, tz_initial),
    ]
    fund_prices = [
        _make_fund_price(MarketDate(2026, 1, 1), 100.0, tz_initial),
        _make_fund_price(MarketDate(2026, 1, 2), 110.0, tz_initial),
        # This correction is for 2026-01-2 but published at tz_correction (future)
        _make_fund_price(MarketDate(2026, 1, 2), 105.0, tz_correction),
    ]

    dataset = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalReconciliationRecord)

    # It must select the initial snapshot, not the correction, because prediction filters it
    assert rec.result.end_snapshot is fund_prices[1]


def test_missing_security_price_is_success_with_coverage_gap() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    holdings = [_make_holding_snap(MarketDate(2026, 1, 1), tz)]
    # Missing end price for INST_A
    prices = [_make_security_price(MarketDate(2026, 1, 1), 10.0, tz)]
    fund_prices = [
        _make_fund_price(MarketDate(2026, 1, 1), 100.0, tz),
        _make_fund_price(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    rec = dataset.outcomes[0]

    assert isinstance(rec, HistoricalReconciliationRecord)
    # The portfolio is missing the end price for the single equity, so coverage is 0.0
    assert rec.return_coverage == 0.0
    # Published is 110/100 - 1 = 0.1, covered contribution is 0, residual is 0.1
    assert rec.published_fund_return == pytest.approx(0.1)
    assert rec.observed_portfolio_contribution == pytest.approx(0.0)
    assert rec.reconciliation_residual == pytest.approx(0.1)


def test_missing_start_fund_price_skips() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    holdings = [_make_holding_snap(MarketDate(2026, 1, 1), tz)]
    prices = [
        _make_security_price(MarketDate(2026, 1, 1), 10.0, tz),
        _make_security_price(MarketDate(2026, 1, 2), 11.0, tz),
    ]
    fund_prices = [_make_fund_price(MarketDate(2026, 1, 2), 110.0, tz)]  # Missing start

    dataset = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    rec = dataset.outcomes[0]

    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 1)


def test_missing_end_fund_price_skips() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    holdings = [_make_holding_snap(MarketDate(2026, 1, 1), tz)]
    prices = [
        _make_security_price(MarketDate(2026, 1, 1), 10.0, tz),
        _make_security_price(MarketDate(2026, 1, 2), 11.0, tz),
    ]
    fund_prices = [_make_fund_price(MarketDate(2026, 1, 1), 100.0, tz)]  # Missing end

    dataset = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    rec = dataset.outcomes[0]

    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingFundPriceSkip)
    assert rec.reason.required_date == MarketDate(2026, 1, 2)


def test_missing_holdings_skips() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    holdings: list[HoldingSnapshot] = []  # Missing
    prices = [
        _make_security_price(MarketDate(2026, 1, 1), 10.0, tz),
        _make_security_price(MarketDate(2026, 1, 2), 11.0, tz),
    ]
    fund_prices = [
        _make_fund_price(MarketDate(2026, 1, 1), 100.0, tz),
        _make_fund_price(MarketDate(2026, 1, 2), 110.0, tz),
    ]

    dataset = build_historical_reconciliation_dataset([req], holdings, prices, fund_prices)
    rec = dataset.outcomes[0]

    assert isinstance(rec, SkippedReconciliationRecord)
    assert isinstance(rec.reason, MissingHoldingsSkip)


def test_duplicate_period_rejects() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req1 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    req2 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    with pytest.raises(DuplicatePeriodError):
        build_historical_reconciliation_dataset([req1, req2], [], [], [])


def test_same_end_date_with_different_period_is_not_reported_as_duplicate() -> None:
    tz = datetime(2026, 1, 3, 10, tzinfo=UTC)
    req1 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 3), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 3)),
        fund_price_source_id="src_f",
    )
    req2 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 3), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3)),
        fund_price_source_id="src_f",
    )

    with pytest.raises(DecreasingPeriodError):
        build_historical_reconciliation_dataset([req1, req2], [], [], [])


def test_decreasing_period_rejects() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req1 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 2), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3)),
        fund_price_source_id="src_f",
    )
    req2 = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    with pytest.raises(DecreasingPeriodError):
        build_historical_reconciliation_dataset([req1, req2], [], [], [])


def test_other_errors_fail_fast() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )

    def fail_holdings() -> typing.Iterable[HoldingSnapshot]:
        raise ValueError("Simulated system failure")
        yield  # type: ignore

    with pytest.raises(ValueError, match="Simulated system failure"):
        build_historical_reconciliation_dataset([req], fail_holdings(), [], [])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("alignment_request", object()),
        ("period", object()),
        ("fund_price_source_id", " "),
    ],
)
def test_invalid_request_fields_reject(field: str, value: object) -> None:
    kwargs = {
        "alignment_request": _make_alignment_req(
            MarketDate(2026, 1, 2),
            datetime(2026, 1, 2, 10, tzinfo=UTC),
        ),
        "period": ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        "fund_price_source_id": "src_f",
    }
    kwargs[field] = value

    with pytest.raises(InvalidHistoricalReconciliationRequestError):
        HistoricalReconciliationRequest(**kwargs)  # type: ignore[arg-type]


def test_legacy_builder_materialization_order() -> None:
    tz = datetime(2026, 1, 2, 10, tzinfo=UTC)
    req = HistoricalReconciliationRequest(
        alignment_request=_make_alignment_req(MarketDate(2026, 1, 1), tz),
        period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        fund_price_source_id="src_f",
    )
    holding = _make_holding_snap(MarketDate(2026, 1, 1), tz)
    sec_price = _make_security_price(MarketDate(2026, 1, 1), 10.0, tz)
    fund_p1 = _make_fund_price(MarketDate(2026, 1, 1), 100.0, tz)
    fund_p2 = _make_fund_price(MarketDate(2026, 1, 2), 110.0, tz)

    consumption_order: list[str] = []

    def req_iter() -> typing.Iterator[HistoricalReconciliationRequest]:
        consumption_order.append("requests")
        yield req

    def holdings_iter() -> typing.Iterator[HoldingSnapshot]:
        consumption_order.append("holdings")
        yield holding

    def prices_iter() -> typing.Iterator[SecurityPriceSnapshot]:
        consumption_order.append("security_prices")
        yield sec_price

    def fund_iter() -> typing.Iterator[FundUnitPriceSnapshot]:
        consumption_order.append("fund_prices")
        yield fund_p1
        yield fund_p2

    build_historical_reconciliation_dataset(
        req_iter(),
        holdings_iter(),
        prices_iter(),
        fund_iter(),
    )

    assert consumption_order == ["requests", "holdings", "security_prices", "fund_prices"]
