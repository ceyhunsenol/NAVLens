"""Field-by-field parity tests comparing source-backed and snapshot-backed FX builders."""

from datetime import date

import pytest
from navlens import MarketDate
from navlens.datasets import FxRateSnapshot
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationDataset,
    HistoricalFxReconciliationRecord,
    MissingFundPriceSkip,
    SkippedFxReconciliationRecord,
    build_historical_fx_reconciliation_dataset,
    build_historical_fx_reconciliation_dataset_from_security_price_source,
)
from tests.historical_fx_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_cash_position,
    make_equity_position,
    make_etf_position,
    make_fund_unit_price_snapshot,
    make_fx_historical_request,
    make_fx_rate_snapshot,
    make_holding_snapshot,
    make_security_price_snapshot,
    make_utc_timestamp,
)


def assert_selected_fx_snapshots_parity(
    source_snaps: tuple[FxRateSnapshot, ...],
    direct_snaps: tuple[FxRateSnapshot, ...],
) -> None:
    assert len(source_snaps) == len(direct_snaps)
    for idx, (s_snap, d_snap) in enumerate(zip(source_snaps, direct_snaps, strict=True)):
        assert s_snap is d_snap, f"Snapshot identity mismatch at index {idx}"
        assert (
            s_snap.observation.pair.base_currency.code == d_snap.observation.pair.base_currency.code
        )
        assert (
            s_snap.observation.pair.quote_currency.code
            == d_snap.observation.pair.quote_currency.code
        )
        assert s_snap.observation.kind.name == d_snap.observation.kind.name
        assert s_snap.observation.market_date == d_snap.observation.market_date
        assert s_snap.observation.rate.quote_currency_per_one_base_currency == pytest.approx(
            d_snap.observation.rate.quote_currency_per_one_base_currency
        )
        assert s_snap.available_at == d_snap.available_at
        assert s_snap.ingested_at == d_snap.ingested_at
        assert s_snap.source_id == d_snap.source_id


def assert_optional_named_value_parity(source_value: object, direct_value: object) -> None:
    assert (source_value is None) == (direct_value is None)
    if source_value is not None:
        assert direct_value is not None
        assert source_value.name == direct_value.name  # type: ignore[attr-defined]


def assert_optional_currency_parity(source_value: object, direct_value: object) -> None:
    assert (source_value is None) == (direct_value is None)
    if source_value is not None:
        assert direct_value is not None
        assert source_value.code == direct_value.code  # type: ignore[attr-defined]


def assert_price_gap_reason_parity(source_reason: object, direct_reason: object) -> None:
    assert source_reason.kind == direct_reason.kind  # type: ignore[attr-defined]
    assert_optional_named_value_parity(
        source_reason.asset_class,
        direct_reason.asset_class,  # type: ignore[attr-defined]
    )
    assert source_reason.observations_found == direct_reason.observations_found  # type: ignore[attr-defined]
    assert source_reason.observations_required == direct_reason.observations_required  # type: ignore[attr-defined]
    assert_optional_currency_parity(
        source_reason.expected_currency,
        direct_reason.expected_currency,  # type: ignore[attr-defined]
    )
    assert_optional_currency_parity(
        source_reason.found_currency,
        direct_reason.found_currency,  # type: ignore[attr-defined]
    )
    assert_optional_named_value_parity(
        source_reason.expected_price_adjustment,  # type: ignore[attr-defined]
        direct_reason.expected_price_adjustment,  # type: ignore[attr-defined]
    )
    assert_optional_named_value_parity(
        source_reason.found_price_adjustment,  # type: ignore[attr-defined]
        direct_reason.found_price_adjustment,  # type: ignore[attr-defined]
    )
    assert source_reason.latest_observation_date == direct_reason.latest_observation_date  # type: ignore[attr-defined]
    assert source_reason.pricing_as_of_date == direct_reason.pricing_as_of_date  # type: ignore[attr-defined]
    assert (  # type: ignore[attr-defined]
        source_reason.max_staleness_calendar_days == direct_reason.max_staleness_calendar_days
    )


def assert_boundary_evidence_parity(source_evidence: object, direct_evidence: object) -> None:
    assert (source_evidence is None) == (direct_evidence is None)
    if source_evidence is None:
        return
    assert direct_evidence is not None
    assert source_evidence.requested_date == direct_evidence.requested_date  # type: ignore[attr-defined]
    assert (  # type: ignore[attr-defined]
        source_evidence.staleness_calendar_days == direct_evidence.staleness_calendar_days
    )
    source_observation = source_evidence.observation  # type: ignore[attr-defined]
    direct_observation = direct_evidence.observation  # type: ignore[attr-defined]
    assert source_observation.market_date == direct_observation.market_date
    assert source_observation.kind.name == direct_observation.kind.name
    assert source_observation.pair.base_currency.code == direct_observation.pair.base_currency.code
    assert (
        source_observation.pair.quote_currency.code == direct_observation.pair.quote_currency.code
    )
    assert source_observation.rate.quote_currency_per_one_base_currency == pytest.approx(
        direct_observation.rate.quote_currency_per_one_base_currency
    )


def assert_return_gap_reason_parity(source_reason: object, direct_reason: object) -> None:
    assert source_reason.kind == direct_reason.kind  # type: ignore[attr-defined]
    source_pair = source_reason.required_pair  # type: ignore[attr-defined]
    direct_pair = direct_reason.required_pair  # type: ignore[attr-defined]
    assert (source_pair is None) == (direct_pair is None)
    if source_pair is not None:
        assert direct_pair is not None
        assert source_pair.base_currency.code == direct_pair.base_currency.code
        assert source_pair.quote_currency.code == direct_pair.quote_currency.code
    assert_optional_named_value_parity(
        source_reason.required_kind,
        direct_reason.required_kind,  # type: ignore[attr-defined]
    )
    source_kinds = source_reason.available_kinds  # type: ignore[attr-defined]
    direct_kinds = direct_reason.available_kinds  # type: ignore[attr-defined]
    assert (source_kinds is None) == (direct_kinds is None)
    if source_kinds is not None:
        assert direct_kinds is not None
        assert [kind.name for kind in source_kinds] == [kind.name for kind in direct_kinds]
    assert source_reason.requested_date == direct_reason.requested_date  # type: ignore[attr-defined]
    assert (  # type: ignore[attr-defined]
        source_reason.maximum_staleness_calendar_days
        == direct_reason.maximum_staleness_calendar_days
    )
    assert_boundary_evidence_parity(
        source_reason.boundary_evidence,
        direct_reason.boundary_evidence,  # type: ignore[attr-defined]
    )


def assert_historical_fx_dataset_parity(
    source_dataset: HistoricalFxReconciliationDataset,
    direct_dataset: HistoricalFxReconciliationDataset,
) -> None:
    """Perform comprehensive field-by-field parity assertions without using generic ==."""
    assert len(source_dataset.outcomes) == len(direct_dataset.outcomes)

    for idx, (source_outcome, direct_outcome) in enumerate(
        zip(source_dataset.outcomes, direct_dataset.outcomes, strict=True)
    ):
        assert type(source_outcome) is type(direct_outcome), f"Outcome type mismatch at index {idx}"
        assert source_outcome.request is direct_outcome.request, (
            f"Request identity mismatch at index {idx}"
        )

        if isinstance(source_outcome, HistoricalFxReconciliationRecord):
            assert isinstance(direct_outcome, HistoricalFxReconciliationRecord)
            # Top-level financial properties
            assert source_outcome.published_fund_return == pytest.approx(
                direct_outcome.published_fund_return
            )
            assert source_outcome.observed_portfolio_contribution == pytest.approx(
                direct_outcome.observed_portfolio_contribution
            )
            assert source_outcome.return_coverage == pytest.approx(direct_outcome.return_coverage)
            assert source_outcome.reconciliation_residual == pytest.approx(
                direct_outcome.reconciliation_residual
            )

            # Direct result references
            assert (
                source_outcome.result.fund_price_source_id
                == direct_outcome.result.fund_price_source_id
            )
            assert source_outcome.result.start_snapshot is direct_outcome.result.start_snapshot
            assert source_outcome.result.end_snapshot is direct_outcome.result.end_snapshot
            assert (
                source_outcome.result.contribution.request.alignment_result.holdings_snapshot
                is direct_outcome.result.contribution.request.alignment_result.holdings_snapshot
            )

            # Selected FX snapshots parity (identity + properties)
            assert_selected_fx_snapshots_parity(
                source_outcome.result.contribution.selected_fx_snapshots,
                direct_outcome.result.contribution.selected_fx_snapshots,
            )

            source_contrib = source_outcome.result.contribution.contribution_result
            direct_contrib = direct_outcome.result.contribution.contribution_result

            assert source_contrib.price_coverage == pytest.approx(direct_contrib.price_coverage)

            # Component contribution level parity
            assert len(source_contrib.component_contributions) == len(
                direct_contrib.component_contributions
            )
            for s_c, d_c in zip(
                source_contrib.component_contributions,
                direct_contrib.component_contributions,
                strict=True,
            ):
                assert s_c.holding.instrument_id == d_c.holding.instrument_id
                assert s_c.holding.asset_class.name == d_c.holding.asset_class.name
                assert s_c.contribution.weight == pytest.approx(d_c.contribution.weight)
                assert s_c.security_period_return.return_decimal == pytest.approx(
                    d_c.security_period_return.return_decimal
                )
                assert s_c.currency_adjustment.is_applied == d_c.currency_adjustment.is_applied
                assert (
                    s_c.currency_adjustment.is_not_required
                    == d_c.currency_adjustment.is_not_required
                )
                if s_c.currency_adjustment.is_applied:
                    assert s_c.currency_adjustment.applied_evidence is not None
                    assert d_c.currency_adjustment.applied_evidence is not None
                    assert s_c.currency_adjustment.applied_evidence.fx_return == pytest.approx(
                        d_c.currency_adjustment.applied_evidence.fx_return
                    )
                assert s_c.effective_base_currency_return == pytest.approx(
                    d_c.effective_base_currency_return
                )
                assert s_c.contribution.weighted_contribution == pytest.approx(
                    d_c.contribution.weighted_contribution
                )
                assert s_c.contribution.market_return == pytest.approx(
                    d_c.contribution.market_return
                )

            # Price gaps parity
            assert len(source_contrib.price_gaps) == len(direct_contrib.price_gaps)
            for s_g, d_g in zip(source_contrib.price_gaps, direct_contrib.price_gaps, strict=True):
                assert s_g.holding.instrument_id == d_g.holding.instrument_id
                assert s_g.holding.asset_class.name == d_g.holding.asset_class.name
                assert_price_gap_reason_parity(s_g.reason, d_g.reason)

            # Return gaps parity
            assert len(source_contrib.return_gaps) == len(direct_contrib.return_gaps)
            for s_rg, d_rg in zip(
                source_contrib.return_gaps, direct_contrib.return_gaps, strict=True
            ):
                assert s_rg.holding.instrument_id == d_rg.holding.instrument_id
                assert s_rg.holding.asset_class.name == d_rg.holding.asset_class.name
                assert_return_gap_reason_parity(s_rg.reason, d_rg.reason)

        elif isinstance(source_outcome, SkippedFxReconciliationRecord):
            assert isinstance(direct_outcome, SkippedFxReconciliationRecord)
            assert type(source_outcome.reason) is type(direct_outcome.reason), (
                f"Skip reason mismatch at index {idx}"
            )
            if isinstance(source_outcome.reason, MissingFundPriceSkip):
                assert isinstance(direct_outcome.reason, MissingFundPriceSkip)
                assert source_outcome.reason.required_date == direct_outcome.reason.required_date


def test_full_coverage_multi_period_fx_parity() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)

    req1 = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_fx_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)
    requests = [req1, req2]

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz1,
            (make_equity_position("AAPL", 0.6), make_etf_position("GLDTR", 0.4)),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("AAPL", 0.5), make_etf_position("GLDTR", 0.5)),
        ),
    ]

    aapl_p1 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 1), 100.0, tz1, currency="USD"
    )
    aapl_p2 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 2), 110.0, tz1, currency="USD"
    )
    aapl_p3 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 3), 121.0, tz2, currency="USD"
    )

    gldtr_p1 = make_security_price_snapshot(
        "GLDTR", MarketDate(2026, 1, 1), 20.0, tz1, currency="TRY"
    )
    gldtr_p2 = make_security_price_snapshot(
        "GLDTR", MarketDate(2026, 1, 2), 21.0, tz1, currency="TRY"
    )
    gldtr_p3 = make_security_price_snapshot(
        "GLDTR", MarketDate(2026, 1, 3), 23.1, tz2, currency="TRY"
    )

    all_prices = [aapl_p1, aapl_p2, aapl_p3, gldtr_p1, gldtr_p2, gldtr_p3]
    source = FakeRecordingSecurityPriceSource(
        data={
            "AAPL": (aapl_p1, aapl_p2, aapl_p3),
            "GLDTR": (gldtr_p1, gldtr_p2, gldtr_p3),
        }
    )

    fx_p1 = make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz1)
    fx_p2 = make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 31.0, tz1)
    fx_p3 = make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 3), 32.0, tz2)
    fx_rates = [fx_p1, fx_p2, fx_p3]

    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 100.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 110.0, tz1),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 121.0, tz2),
    ]

    direct_dataset = build_historical_fx_reconciliation_dataset(
        requests, holdings, all_prices, fx_rates, fund_prices
    )
    source_dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        requests,
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_fx_dataset_parity(source_dataset, direct_dataset)


def test_partial_security_coverage_market_gap_parity() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (
                make_equity_position("AAPL", 0.5),
                make_equity_position("MSFT", 0.3),
                make_cash_position("TRY_CASH", 0.2),
            ),
        )
    ]

    # MSFT has missing end price (market gap)
    aapl_p1 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD"
    )
    aapl_p2 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 2), 110.0, tz, currency="USD"
    )
    msft_p1 = make_security_price_snapshot(
        "MSFT", MarketDate(2026, 1, 1), 200.0, tz, currency="USD"
    )

    all_prices = [aapl_p1, aapl_p2, msft_p1]
    source = FakeRecordingSecurityPriceSource(
        data={
            "AAPL": (aapl_p1, aapl_p2),
            "MSFT": (msft_p1,),
        }
    )

    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 1), 30.0, tz),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 31.0, tz),
    ]

    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz),
    ]

    direct_dataset = build_historical_fx_reconciliation_dataset(
        [req], holdings, all_prices, fx_rates, fund_prices
    )
    source_dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_fx_dataset_parity(source_dataset, direct_dataset)


def test_missing_fx_rate_gap_parity() -> None:
    tz = make_utc_timestamp(2026, 1, 2)
    req = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz)

    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 1),
            tz,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    aapl_p1 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 1), 100.0, tz, currency="USD"
    )
    aapl_p2 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 2), 110.0, tz, currency="USD"
    )

    all_prices = [aapl_p1, aapl_p2]
    source = FakeRecordingSecurityPriceSource(data={"AAPL": (aapl_p1, aapl_p2)})

    # No FX snapshots provided
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 1), 10.0, tz),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.5, tz),
    ]

    direct_dataset = build_historical_fx_reconciliation_dataset(
        [req], holdings, all_prices, [], fund_prices
    )
    source_dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_fx_dataset_parity(source_dataset, direct_dataset)


def test_stale_fx_rate_gap_parity_preserves_boundary_evidence() -> None:
    prediction_time = make_utc_timestamp(2026, 1, 10)
    req = make_fx_historical_request(
        MarketDate(2026, 1, 9),
        MarketDate(2026, 1, 10),
        prediction_time,
    )
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 9),
            prediction_time,
            (make_equity_position("AAPL", 1.0),),
        )
    ]
    start_price = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 9), 100.0, prediction_time, currency="USD"
    )
    end_price = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 10), 105.0, prediction_time, currency="USD"
    )
    all_prices = [start_price, end_price]
    source = FakeRecordingSecurityPriceSource(data={"AAPL": (start_price, end_price)})
    stale_fx = make_fx_rate_snapshot("USD", "TRY", MarketDate(2025, 12, 20), 30.0, prediction_time)
    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 9), 10.0, prediction_time),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 10), 10.5, prediction_time),
    ]

    direct_dataset = build_historical_fx_reconciliation_dataset(
        [req], holdings, all_prices, [stale_fx], fund_prices
    )
    source_dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        [req],
        holdings,
        source,
        [stale_fx],
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_fx_dataset_parity(source_dataset, direct_dataset)


def test_mixed_skips_fx_parity() -> None:
    tz1 = make_utc_timestamp(2026, 1, 2)
    tz2 = make_utc_timestamp(2026, 1, 3)
    tz3 = make_utc_timestamp(2026, 1, 4)

    req1 = make_fx_historical_request(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2), tz1)
    req2 = make_fx_historical_request(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3), tz2)
    req3 = make_fx_historical_request(MarketDate(2026, 1, 3), MarketDate(2026, 1, 4), tz3)
    requests = [req1, req2, req3]

    # req1 has missing holdings, req2 is successful, req3 has missing end fund price
    holdings = [
        make_holding_snapshot(
            MarketDate(2026, 1, 2),
            tz2,
            (make_equity_position("AAPL", 1.0),),
        ),
        make_holding_snapshot(
            MarketDate(2026, 1, 3),
            tz3,
            (make_equity_position("AAPL", 1.0),),
        ),
    ]

    aapl_p2 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 2), 100.0, tz2, currency="USD"
    )
    aapl_p3 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 3), 110.0, tz2, currency="USD"
    )
    aapl_p4 = make_security_price_snapshot(
        "AAPL", MarketDate(2026, 1, 4), 120.0, tz3, currency="USD"
    )

    all_prices = [aapl_p2, aapl_p3, aapl_p4]
    source = FakeRecordingSecurityPriceSource(data={"AAPL": (aapl_p2, aapl_p3, aapl_p4)})

    fx_rates = [
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 2), 30.0, tz2),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 3), 31.0, tz2),
        make_fx_rate_snapshot("USD", "TRY", MarketDate(2026, 1, 4), 32.0, tz3),
    ]

    fund_prices = [
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 2), 10.0, tz2),
        make_fund_unit_price_snapshot(MarketDate(2026, 1, 3), 11.0, tz2),
    ]

    direct_dataset = build_historical_fx_reconciliation_dataset(
        requests, holdings, all_prices, fx_rates, fund_prices
    )
    source_dataset = build_historical_fx_reconciliation_dataset_from_security_price_source(
        requests,
        holdings,
        source,
        fx_rates,
        fund_prices,
        price_history_start_date=date(2026, 1, 1),
    )

    assert_historical_fx_dataset_parity(source_dataset, direct_dataset)
