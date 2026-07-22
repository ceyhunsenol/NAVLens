use navlens_application::{
    AlignmentContractError, AlignmentPolicy, CoverageGapReason, SecurityPriceHistoryCandidate,
};
use navlens_calendar::{MarketDate, PriceAdjustment, SecurityPriceObservation};
use navlens_core::{AssetClass, CurrencyCode, InstrumentId, UnitPrice};

fn sample_date() -> MarketDate {
    MarketDate::new(2023, 1, 1).unwrap()
}

fn sample_currency() -> CurrencyCode {
    CurrencyCode::new("USD").unwrap()
}

fn sample_instrument() -> InstrumentId {
    InstrumentId::new("AAPL").unwrap()
}

#[test]
fn policy_rejects_minimum_observations_less_than_two() {
    let err = AlignmentPolicy::new(
        sample_currency(),
        PriceAdjustment::TotalReturnAdjusted,
        sample_date(),
        1,
        5,
    )
    .unwrap_err();

    assert_eq!(
        err,
        AlignmentContractError::InvalidMinimumObservations { found: 1 }
    );
}

#[test]
fn policy_accepts_valid_parameters() {
    let policy = AlignmentPolicy::new(
        sample_currency(),
        PriceAdjustment::TotalReturnAdjusted,
        sample_date(),
        2,
        5,
    )
    .unwrap();

    assert_eq!(policy.minimum_observations(), 2);
    assert_eq!(policy.max_staleness_calendar_days(), 5);
    assert_eq!(policy.fund_base_currency(), &sample_currency());
    assert_eq!(
        policy.required_price_adjustment(),
        PriceAdjustment::TotalReturnAdjusted
    );
    assert_eq!(policy.pricing_as_of_date(), sample_date());
}

#[test]
fn candidate_rejects_empty_observations() {
    let instrument_id = sample_instrument();
    let err = SecurityPriceHistoryCandidate::new(instrument_id.clone(), vec![]).unwrap_err();
    assert_eq!(
        err,
        AlignmentContractError::EmptyHistoryCandidate { instrument_id }
    );
}

#[test]
fn candidate_rejects_instrument_id_mismatch() {
    let wrong_instrument = InstrumentId::new("MSFT").unwrap();
    let obs = SecurityPriceObservation::new(
        wrong_instrument,
        sample_date(),
        UnitPrice::new(100.0).unwrap(),
        sample_currency(),
        PriceAdjustment::TotalReturnAdjusted,
    );

    let err = SecurityPriceHistoryCandidate::new(sample_instrument(), vec![obs]).unwrap_err();
    assert_eq!(
        err,
        AlignmentContractError::CandidateInstrumentMismatch {
            expected: sample_instrument(),
            found: InstrumentId::new("MSFT").unwrap(),
        }
    );
}

#[test]
fn candidate_accepts_valid_observations() {
    let instrument = sample_instrument();
    let obs = SecurityPriceObservation::new(
        instrument.clone(),
        sample_date(),
        UnitPrice::new(100.0).unwrap(),
        sample_currency(),
        PriceAdjustment::TotalReturnAdjusted,
    );

    let candidate =
        SecurityPriceHistoryCandidate::new(instrument.clone(), vec![obs.clone()]).unwrap();
    assert_eq!(candidate.instrument_id(), &instrument);
    assert_eq!(candidate.observations().len(), 1);
}

#[test]
fn coverage_gap_reason_taxonomy() {
    let reasons = [
        CoverageGapReason::UnsupportedAssetClass {
            asset_class: AssetClass::Derivative,
        },
        CoverageGapReason::MissingPriceSeries,
        CoverageGapReason::InsufficientObservations {
            found: 1,
            required: 2,
        },
        CoverageGapReason::CurrencyMismatch {
            expected: sample_currency(),
            found: CurrencyCode::new("EUR").unwrap(),
        },
        CoverageGapReason::IncompatiblePriceAdjustment {
            expected: PriceAdjustment::TotalReturnAdjusted,
            found: PriceAdjustment::Unadjusted,
        },
        CoverageGapReason::StalePrices {
            latest_observation_date: sample_date(),
            pricing_as_of_date: MarketDate::new(2023, 1, 10).unwrap(),
            max_staleness_calendar_days: 5,
        },
    ];

    assert_eq!(reasons.len(), 6);
    assert_eq!(
        reasons[0],
        CoverageGapReason::UnsupportedAssetClass {
            asset_class: AssetClass::Derivative,
        }
    );
    assert_eq!(reasons[1], CoverageGapReason::MissingPriceSeries);
    assert!(matches!(
        reasons[2],
        CoverageGapReason::InsufficientObservations {
            found: 1,
            required: 2
        }
    ));
    assert!(matches!(
        &reasons[3],
        CoverageGapReason::CurrencyMismatch { expected, found }
            if expected.as_str() == "USD" && found.as_str() == "EUR"
    ));
    assert!(matches!(
        reasons[4],
        CoverageGapReason::IncompatiblePriceAdjustment {
            expected: PriceAdjustment::TotalReturnAdjusted,
            found: PriceAdjustment::Unadjusted
        }
    ));
    assert!(matches!(
        reasons[5],
        CoverageGapReason::StalePrices {
            latest_observation_date,
            pricing_as_of_date,
            max_staleness_calendar_days: 5,
        } if latest_observation_date == sample_date()
            && pricing_as_of_date == MarketDate::new(2023, 1, 10).unwrap()
    ));
}
