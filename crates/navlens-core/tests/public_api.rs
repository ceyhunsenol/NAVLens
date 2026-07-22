use navlens_core::{
    AssetClass, ConfidenceLevel, CoreError, CurrencyCode, DecimalReturn, ExpenseRate, FundId,
    HoldingPosition, InstrumentId, PortfolioComponent, PortfolioCoverageWeights, PortfolioEstimate,
    PortfolioReturnContribution, PortfolioWeight, PredictionInterval, UnitPrice,
    calculate_decimal_return,
};

fn decimal_return(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return should be finite")
}

fn expense_rate(value: f64) -> ExpenseRate {
    ExpenseRate::new(value).expect("test expense rate should be valid")
}

fn portfolio_weight(value: f64) -> PortfolioWeight {
    PortfolioWeight::new(value).expect("test portfolio weight should be valid")
}

#[test]
fn calculates_weighted_return_after_expenses() {
    let components = [
        PortfolioComponent {
            weight: portfolio_weight(0.7),
            market_return: decimal_return(0.02),
        },
        PortfolioComponent {
            weight: portfolio_weight(0.2),
            market_return: decimal_return(-0.01),
        },
        PortfolioComponent {
            weight: portfolio_weight(0.1),
            market_return: decimal_return(0.001),
        },
    ];
    let estimate = PortfolioEstimate {
        components: &components,
        daily_expense_rate: expense_rate(0.0001),
    };

    let result = estimate.calculate().expect("valid portfolio");
    assert!((result.value() - 0.012).abs() < 1e-12);
}

#[test]
fn rejects_invalid_weight_sum() {
    let components = [PortfolioComponent {
        weight: portfolio_weight(0.8),
        market_return: decimal_return(0.01),
    }];
    let estimate = PortfolioEstimate {
        components: &components,
        daily_expense_rate: expense_rate(0.0),
    };

    assert_eq!(
        estimate.calculate(),
        Err(CoreError::WeightsDoNotSumToOne(0.8))
    );
}

#[test]
fn rejects_non_finite_returns() {
    assert_eq!(
        DecimalReturn::new(f64::NAN),
        Err(CoreError::NonFiniteNumber)
    );
}

#[test]
fn rejects_out_of_range_weights_and_expenses() {
    assert_eq!(
        PortfolioWeight::new(1.01),
        Err(CoreError::PortfolioWeightOutOfRange(1.01))
    );
    assert_eq!(
        ExpenseRate::new(-0.01),
        Err(CoreError::ExpenseRateOutOfRange(-0.01))
    );
}

#[test]
fn validates_fund_identifiers() {
    let fund_id = FundId::new("ABC").expect("valid fund identifier");
    assert_eq!(fund_id.as_str(), "ABC");
    assert_eq!(fund_id.to_string(), "ABC");
    assert_eq!(
        FundId::new("ABC 123"),
        Err(CoreError::FundIdContainsWhitespace)
    );
}

#[test]
fn creates_provider_neutral_holding_positions() {
    let instrument_id = InstrumentId::new("US67066G1040").expect("valid ISIN");
    let position =
        HoldingPosition::new(instrument_id, AssetClass::Equity, portfolio_weight(0.0544));

    assert_eq!(position.instrument_id().as_str(), "US67066G1040");
    assert_eq!(position.asset_class(), AssetClass::Equity);
    assert!((position.fund_total_weight().value() - 0.0544).abs() < f64::EPSILON);
}

#[test]
fn rejects_non_normalized_instrument_identifiers() {
    assert_eq!(
        InstrumentId::new("AAPL US"),
        Err(CoreError::InstrumentIdContainsWhitespace)
    );
    assert_eq!(InstrumentId::new(""), Err(CoreError::EmptyInstrumentId));
    assert_eq!(
        InstrumentId::new("X".repeat(InstrumentId::MAX_LENGTH + 1)),
        Err(CoreError::InstrumentIdTooLong(InstrumentId::MAX_LENGTH + 1))
    );
    assert_eq!(
        InstrumentId::new("ABC\0"),
        Err(CoreError::InstrumentIdContainsControlCharacter)
    );
}

#[test]
fn validates_confidence_levels() {
    let confidence = ConfidenceLevel::new(0.9).expect("valid confidence level");
    assert!((confidence.value() - 0.9).abs() < f64::EPSILON);
    assert_eq!(
        ConfidenceLevel::new(1.0),
        Err(CoreError::ConfidenceLevelOutOfRange(1.0))
    );
}

#[test]
fn validates_prediction_intervals() {
    let confidence = ConfidenceLevel::new(0.9).expect("valid confidence level");
    let interval = PredictionInterval::new(decimal_return(-0.01), decimal_return(0.03), confidence)
        .expect("valid prediction interval");

    assert!(interval.contains(decimal_return(0.02)));
    assert!(!interval.contains(decimal_return(0.04)));
    assert!((interval.width() - 0.04).abs() < f64::EPSILON);
    assert_eq!(
        PredictionInterval::new(decimal_return(0.03), decimal_return(-0.01), confidence),
        Err(CoreError::PredictionIntervalBounds {
            lower: 0.03,
            upper: -0.01,
        })
    );
}

#[test]
fn calculates_decimal_return_from_unit_prices() {
    let previous = UnitPrice::new(100.0).expect("valid previous price");
    let current = UnitPrice::new(101.0).expect("valid current price");

    let result = calculate_decimal_return(previous, current).expect("finite return");

    assert!((result.value() - 0.01).abs() < 1e-12);
}

#[test]
fn rejects_invalid_unit_prices() {
    assert_eq!(
        UnitPrice::new(0.0),
        Err(CoreError::UnitPriceNotPositive(0.0))
    );
    assert_eq!(
        UnitPrice::new(-1.0),
        Err(CoreError::UnitPriceNotPositive(-1.0))
    );
    assert_eq!(UnitPrice::new(f64::NAN), Err(CoreError::NonFiniteNumber));
}

#[test]
fn creates_currency_codes() {
    let usd = CurrencyCode::new("USD").expect("valid currency");
    assert_eq!(usd.as_str(), "USD");
    assert_eq!(usd.as_ref(), "USD");
    assert_eq!(usd.to_string(), "USD");

    let try_code = CurrencyCode::new("TRY").expect("valid currency");
    assert_ne!(usd, try_code);
    assert!(usd > try_code);

    let mut codes = std::collections::HashSet::new();
    assert!(codes.insert(usd.clone()));
    assert!(!codes.insert(CurrencyCode::new("USD").expect("same valid currency")));
    assert!(codes.contains(&usd));
}

#[test]
fn rejects_invalid_currency_codes() {
    for invalid in ["", "US", "USDT", "usd", "US1", "US ", "US\0", "ÜS"] {
        assert_eq!(
            CurrencyCode::new(invalid),
            Err(CoreError::InvalidCurrencyCode),
            "unexpectedly accepted {invalid:?}"
        );
    }
}

#[test]
fn calculates_portfolio_coverage_weights_full_coverage() {
    let covered = [portfolio_weight(0.6), portfolio_weight(0.4)];
    let uncovered = [];

    let coverage = PortfolioCoverageWeights::new(&covered, &uncovered).expect("valid coverage");

    assert!((coverage.declared_weight().value() - 1.0).abs() < f64::EPSILON);
    assert!((coverage.covered_weight().value() - 1.0).abs() < f64::EPSILON);
    assert!((coverage.uncovered_listed_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.unrepresented_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.total_uncovered_weight().value() - 0.0).abs() < f64::EPSILON);
    assert_eq!(coverage.coverage_ratio(), coverage.covered_weight());
}

#[test]
fn calculates_portfolio_coverage_weights_partial_coverage() {
    let covered = [portfolio_weight(0.5)];
    let uncovered = [portfolio_weight(0.3)];

    let coverage = PortfolioCoverageWeights::new(&covered, &uncovered).expect("valid coverage");

    assert!((coverage.declared_weight().value() - 0.8).abs() < f64::EPSILON);
    assert!((coverage.covered_weight().value() - 0.5).abs() < f64::EPSILON);
    assert!((coverage.uncovered_listed_weight().value() - 0.3).abs() < f64::EPSILON);
    assert!((coverage.unrepresented_weight().value() - 0.2).abs() < f64::EPSILON);
    assert!((coverage.total_uncovered_weight().value() - 0.5).abs() < f64::EPSILON);
    assert_eq!(coverage.coverage_ratio(), coverage.covered_weight());
}

#[test]
fn calculates_portfolio_coverage_weights_empty_inputs() {
    let covered = [];
    let uncovered = [];

    let coverage = PortfolioCoverageWeights::new(&covered, &uncovered).expect("valid coverage");

    assert!((coverage.declared_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.covered_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.uncovered_listed_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.unrepresented_weight().value() - 1.0).abs() < f64::EPSILON);
    assert!((coverage.total_uncovered_weight().value() - 1.0).abs() < f64::EPSILON);
    assert_eq!(coverage.coverage_ratio(), coverage.covered_weight());
}

#[test]
fn calculates_portfolio_coverage_weights_completely_uncovered() {
    let covered = [];
    let uncovered = [portfolio_weight(0.7)];

    let coverage = PortfolioCoverageWeights::new(&covered, &uncovered).expect("valid coverage");

    assert!((coverage.declared_weight().value() - 0.7).abs() < f64::EPSILON);
    assert!((coverage.covered_weight().value() - 0.0).abs() < f64::EPSILON);
    assert!((coverage.uncovered_listed_weight().value() - 0.7).abs() < f64::EPSILON);
    assert!((coverage.unrepresented_weight().value() - 0.3).abs() < f64::EPSILON);
    assert!((coverage.total_uncovered_weight().value() - 1.0).abs() < f64::EPSILON);
    assert_eq!(coverage.coverage_ratio(), coverage.covered_weight());
}

#[test]
fn rejects_portfolio_coverage_weights_exceeding_one() {
    let covered = [portfolio_weight(0.8)];
    let uncovered = [portfolio_weight(0.3)];

    assert_eq!(
        PortfolioCoverageWeights::new(&covered, &uncovered),
        Err(CoreError::DeclaredWeightExceedsFundTotal(1.1))
    );
}

#[test]
fn calculates_portfolio_return_contribution_empty_input() {
    let contribution =
        PortfolioReturnContribution::calculate(&[]).expect("empty components should succeed");

    assert!((contribution.observed_contribution().value() - 0.0).abs() < f64::EPSILON);
    assert!((contribution.return_coverage().value() - 0.0).abs() < f64::EPSILON);
    assert!(!contribution.has_full_coverage());
}

#[test]
fn calculates_partial_portfolio_return_contribution_without_renormalization() {
    let components = [
        PortfolioComponent {
            weight: portfolio_weight(0.4),
            market_return: decimal_return(0.05),
        },
        PortfolioComponent {
            weight: portfolio_weight(0.2),
            market_return: decimal_return(-0.03),
        },
    ];

    let contribution =
        PortfolioReturnContribution::calculate(&components).expect("valid partial components");

    assert!((contribution.observed_contribution().value() - 0.014).abs() < 1e-12);
    assert!((contribution.return_coverage().value() - 0.6).abs() < 1e-12);
    assert!(!contribution.has_full_coverage());
}

#[test]
fn calculates_full_coverage_portfolio_return_contribution() {
    let components = [
        PortfolioComponent {
            weight: portfolio_weight(0.7),
            market_return: decimal_return(0.02),
        },
        PortfolioComponent {
            weight: portfolio_weight(0.3),
            market_return: decimal_return(-0.01),
        },
    ];

    let contribution = PortfolioReturnContribution::calculate(&components)
        .expect("valid full coverage components");

    assert!((contribution.observed_contribution().value() - 0.011).abs() < 1e-12);
    assert!((contribution.return_coverage().value() - 1.0).abs() < 1e-12);
    assert!(contribution.has_full_coverage());
}

#[test]
fn clamps_return_coverage_within_tolerance_and_rejects_exceeding_weight() {
    let w1 = 0.75;
    let w2 = 0.250_000_000_5;
    let raw_sum = w1 + w2;
    assert!(raw_sum > 1.0);
    assert!(raw_sum < 1.0 + 1e-9);

    let components_within_tolerance = [
        PortfolioComponent {
            weight: portfolio_weight(w1),
            market_return: decimal_return(0.01),
        },
        PortfolioComponent {
            weight: portfolio_weight(w2),
            market_return: decimal_return(0.01),
        },
    ];

    let clamped = PortfolioReturnContribution::calculate(&components_within_tolerance)
        .expect("within tolerance should succeed");
    assert!((clamped.return_coverage().value() - 1.0).abs() < f64::EPSILON);
    assert!(clamped.has_full_coverage());

    // 0.8 + 0.3 = 1.1 (exceeds 1.0 + tolerance)
    let components_exceeding = [
        PortfolioComponent {
            weight: portfolio_weight(0.8),
            market_return: decimal_return(0.01),
        },
        PortfolioComponent {
            weight: portfolio_weight(0.3),
            market_return: decimal_return(0.01),
        },
    ];

    assert_eq!(
        PortfolioReturnContribution::calculate(&components_exceeding),
        Err(CoreError::ReturnCoverageExceedsFundTotal(1.1))
    );
}
