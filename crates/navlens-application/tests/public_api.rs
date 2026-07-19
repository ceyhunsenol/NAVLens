use navlens_application::{
    ApplicationError, EstimatePortfolioReturnCommand, WeightedMarketReturnInput,
    estimate_portfolio_return,
};
use navlens_core::CoreError;

#[test]
fn estimates_portfolio_return_through_application_boundary() {
    let command = EstimatePortfolioReturnCommand::new(
        vec![
            WeightedMarketReturnInput::new(0.7, 0.02),
            WeightedMarketReturnInput::new(0.2, -0.01),
            WeightedMarketReturnInput::new(0.1, 0.001),
        ],
        0.0001,
    );

    let result = estimate_portfolio_return(&command).expect("valid estimate command");
    assert!((result.estimated_return().value() - 0.012).abs() < 1e-12);
}

#[test]
fn maps_domain_validation_to_application_error() {
    let command =
        EstimatePortfolioReturnCommand::new(vec![WeightedMarketReturnInput::new(1.2, 0.02)], 0.0);

    assert_eq!(
        estimate_portfolio_return(&command),
        Err(ApplicationError::InvalidEstimateInput(
            CoreError::PortfolioWeightOutOfRange(1.2)
        ))
    );
}
