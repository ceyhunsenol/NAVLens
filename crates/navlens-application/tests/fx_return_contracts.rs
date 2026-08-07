use navlens_application::{
    CurrencyReturnAdjustment, FxAdjustmentEvidence, FxBoundaryEvidence, FxReturnContractError,
    FxReturnPolicy, ReturnCoverageGapReason,
};
use navlens_calendar::{FxRateObservation, MarketDate};
use navlens_core::{
    CurrencyCode, CurrencyPair, DecimalReturn, FxRate, FxRateKind, calculate_fx_decimal_return,
};

fn usd_try() -> CurrencyPair {
    CurrencyPair::new(
        CurrencyCode::new("USD").unwrap(),
        CurrencyCode::new("TRY").unwrap(),
    )
    .unwrap()
}

fn eur_try() -> CurrencyPair {
    CurrencyPair::new(
        CurrencyCode::new("EUR").unwrap(),
        CurrencyCode::new("TRY").unwrap(),
    )
    .unwrap()
}

fn make_obs(
    pair: CurrencyPair,
    year: i32,
    month: u8,
    day: u8,
    rate_val: f64,
    kind: FxRateKind,
) -> FxRateObservation {
    FxRateObservation::new(
        pair,
        MarketDate::new(year, month, day).unwrap(),
        FxRate::new(rate_val).unwrap(),
        kind,
    )
}

#[test]
fn policy_preserves_kind_and_zero_staleness() {
    let policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    assert_eq!(policy.required_fx_rate_kind(), FxRateKind::NonCashBuying);
    assert_eq!(policy.max_fx_staleness_calendar_days(), 0);
}

#[test]
fn policy_preserves_non_zero_staleness() {
    let policy = FxReturnPolicy::new(FxRateKind::NonCashSelling, 5);

    assert_eq!(policy.required_fx_rate_kind(), FxRateKind::NonCashSelling);
    assert_eq!(policy.max_fx_staleness_calendar_days(), 5);
}

#[test]
fn creates_exact_date_boundary_evidence() {
    let date = MarketDate::new(2026, 1, 15).unwrap();
    let obs = make_obs(usd_try(), 2026, 1, 15, 35.0, FxRateKind::NonCashBuying);

    let evidence = FxBoundaryEvidence::new(date, obs.clone(), 0).expect("valid exact evidence");

    assert_eq!(evidence.requested_date(), date);
    assert_eq!(evidence.observation(), &obs);
    assert_eq!(evidence.staleness_calendar_days(), 0);
}

#[test]
fn creates_valid_stale_boundary_evidence() {
    let req_date = MarketDate::new(2026, 1, 15).unwrap();
    let obs = make_obs(usd_try(), 2026, 1, 12, 35.0, FxRateKind::NonCashBuying);

    let evidence = FxBoundaryEvidence::new(req_date, obs.clone(), 3).expect("valid stale evidence");

    assert_eq!(evidence.requested_date(), req_date);
    assert_eq!(
        evidence.observation().market_date(),
        MarketDate::new(2026, 1, 12).unwrap()
    );
    assert_eq!(evidence.staleness_calendar_days(), 3);
}

#[test]
fn rejects_future_observation_for_boundary_evidence() {
    let req_date = MarketDate::new(2026, 1, 15).unwrap();
    let obs = make_obs(usd_try(), 2026, 1, 16, 35.0, FxRateKind::NonCashBuying);

    assert_eq!(
        FxBoundaryEvidence::new(req_date, obs, 0),
        Err(FxReturnContractError::ObservationAfterRequestedBoundary {
            requested_date: req_date,
            observation_date: MarketDate::new(2026, 1, 16).unwrap(),
        })
    );
}

#[test]
fn rejects_incorrect_declared_staleness() {
    let req_date = MarketDate::new(2026, 1, 15).unwrap();
    let obs = make_obs(usd_try(), 2026, 1, 12, 35.0, FxRateKind::NonCashBuying);

    assert_eq!(
        FxBoundaryEvidence::new(req_date, obs, 2),
        Err(FxReturnContractError::StalenessMismatch {
            requested_date: req_date,
            observation_date: MarketDate::new(2026, 1, 12).unwrap(),
            declared: 2,
            actual: 3,
        })
    );
}

#[test]
fn creates_valid_adjustment_evidence_and_delegates_getters() {
    let start_obs = make_obs(usd_try(), 2026, 1, 10, 30.0, FxRateKind::NonCashBuying);
    let end_obs = make_obs(usd_try(), 2026, 1, 20, 33.0, FxRateKind::NonCashBuying);

    let start_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 10).unwrap(), start_obs, 0).unwrap();
    let end_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 20).unwrap(), end_obs, 0).unwrap();

    let expected_return =
        calculate_fx_decimal_return(start_ev.observation().rate(), end_ev.observation().rate())
            .unwrap();

    let adj_ev = FxAdjustmentEvidence::new(start_ev.clone(), end_ev.clone(), expected_return)
        .expect("valid adjustment evidence");

    assert_eq!(adj_ev.start(), &start_ev);
    assert_eq!(adj_ev.end(), &end_ev);
    assert_eq!(adj_ev.fx_return(), expected_return);
    assert_eq!(adj_ev.pair(), &usd_try());
    assert_eq!(adj_ev.kind(), FxRateKind::NonCashBuying);
}

#[test]
fn rejects_boundary_pair_mismatch() {
    let start_obs = make_obs(usd_try(), 2026, 1, 10, 30.0, FxRateKind::NonCashBuying);
    let end_obs = make_obs(eur_try(), 2026, 1, 20, 35.0, FxRateKind::NonCashBuying);

    let start_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 10).unwrap(), start_obs, 0).unwrap();
    let end_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 20).unwrap(), end_obs, 0).unwrap();

    let dummy_return = DecimalReturn::new(0.1).unwrap();

    assert_eq!(
        FxAdjustmentEvidence::new(start_ev, end_ev, dummy_return),
        Err(FxReturnContractError::BoundaryCurrencyPairMismatch {
            start_pair: usd_try(),
            end_pair: eur_try(),
        })
    );
}

#[test]
fn rejects_boundary_rate_kind_mismatch() {
    let start_obs = make_obs(usd_try(), 2026, 1, 10, 30.0, FxRateKind::NonCashBuying);
    let end_obs = make_obs(usd_try(), 2026, 1, 20, 33.0, FxRateKind::NonCashSelling);

    let start_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 10).unwrap(), start_obs, 0).unwrap();
    let end_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 20).unwrap(), end_obs, 0).unwrap();

    let dummy_return = DecimalReturn::new(0.1).unwrap();

    assert_eq!(
        FxAdjustmentEvidence::new(start_ev, end_ev, dummy_return),
        Err(FxReturnContractError::BoundaryFxRateKindMismatch {
            start_kind: FxRateKind::NonCashBuying,
            end_kind: FxRateKind::NonCashSelling,
        })
    );
}

#[test]
fn rejects_incorrect_supplied_fx_return() {
    let start_obs = make_obs(usd_try(), 2026, 1, 10, 30.0, FxRateKind::NonCashBuying);
    let end_obs = make_obs(usd_try(), 2026, 1, 20, 33.0, FxRateKind::NonCashBuying);

    let start_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 10).unwrap(), start_obs, 0).unwrap();
    let end_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 20).unwrap(), end_obs, 0).unwrap();

    let canonical_return =
        calculate_fx_decimal_return(start_ev.observation().rate(), end_ev.observation().rate())
            .unwrap();
    let wrong_return = DecimalReturn::new(0.999).unwrap();

    assert_eq!(
        FxAdjustmentEvidence::new(start_ev, end_ev, wrong_return),
        Err(FxReturnContractError::FxReturnMismatch {
            supplied: wrong_return,
            calculated: canonical_return,
        })
    );
}

#[test]
fn currency_return_adjustment_variants_remain_distinguishable() {
    let not_req = CurrencyReturnAdjustment::NotRequired;

    let start_obs = make_obs(usd_try(), 2026, 1, 10, 30.0, FxRateKind::NonCashBuying);
    let end_obs = make_obs(usd_try(), 2026, 1, 20, 33.0, FxRateKind::NonCashBuying);

    let start_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 10).unwrap(), start_obs, 0).unwrap();
    let end_ev =
        FxBoundaryEvidence::new(MarketDate::new(2026, 1, 20).unwrap(), end_obs, 0).unwrap();

    let fx_ret =
        calculate_fx_decimal_return(start_ev.observation().rate(), end_ev.observation().rate())
            .unwrap();

    let adj_ev = FxAdjustmentEvidence::new(start_ev, end_ev, fx_ret).unwrap();
    let applied = CurrencyReturnAdjustment::Applied(adj_ev.clone());

    assert_ne!(not_req, applied);
    match applied {
        CurrencyReturnAdjustment::Applied(ev) => assert_eq!(ev, adj_ev),
        CurrencyReturnAdjustment::NotRequired => panic!("expected Applied variant"),
    }
}

#[test]
fn fx_return_gap_variants_preserve_their_typed_context() {
    let pair = usd_try();
    let kind = FxRateKind::NonCashBuying;
    let requested_date = MarketDate::new(2026, 1, 15).unwrap();
    let observation = make_obs(pair.clone(), 2026, 1, 12, 35.0, kind);
    let evidence = FxBoundaryEvidence::new(requested_date, observation, 3).unwrap();

    let reasons = [
        ReturnCoverageGapReason::MissingDirectFxCandidate {
            required_pair: pair.clone(),
            required_kind: kind,
        },
        ReturnCoverageGapReason::FxRateKindMismatch {
            required_pair: pair.clone(),
            required_kind: kind,
            available_kinds: vec![FxRateKind::NonCashSelling],
        },
        ReturnCoverageGapReason::MissingFxStartObservation {
            required_pair: pair.clone(),
            required_kind: kind,
            requested_date,
        },
        ReturnCoverageGapReason::StaleFxStartObservation {
            evidence: evidence.clone(),
            maximum_staleness_calendar_days: 2,
        },
        ReturnCoverageGapReason::StaleFxEndObservation {
            evidence: evidence.clone(),
            maximum_staleness_calendar_days: 2,
        },
    ];

    assert!(matches!(
        reasons[0],
        ReturnCoverageGapReason::MissingDirectFxCandidate { .. }
    ));
    assert!(matches!(
        reasons[1],
        ReturnCoverageGapReason::FxRateKindMismatch { .. }
    ));
    assert!(matches!(
        reasons[2],
        ReturnCoverageGapReason::MissingFxStartObservation { .. }
    ));
    assert!(matches!(
        reasons[4],
        ReturnCoverageGapReason::StaleFxEndObservation { .. }
    ));

    for reason in [&reasons[3], &reasons[4]] {
        let (ReturnCoverageGapReason::StaleFxStartObservation {
            evidence: stored_evidence,
            ..
        }
        | ReturnCoverageGapReason::StaleFxEndObservation {
            evidence: stored_evidence,
            ..
        }) = reason
        else {
            panic!("expected a stale FX boundary gap");
        };
        assert_eq!(stored_evidence.requested_date(), requested_date);
        assert_eq!(
            stored_evidence.observation().market_date(),
            MarketDate::new(2026, 1, 12).unwrap()
        );
        assert_eq!(stored_evidence.staleness_calendar_days(), 3);
    }
}
