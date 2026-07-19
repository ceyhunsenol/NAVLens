use navlens_core::{
    CoreError, DecimalReturn, ExpenseRate, FundId, PortfolioComponent, PortfolioEstimate,
    PortfolioWeight,
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
